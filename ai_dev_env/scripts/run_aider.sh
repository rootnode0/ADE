#!/bin/bash

set +e

START_TIME=$(date +%s)
LOG_SEQ=0

log() {
  LOG_SEQ=$((LOG_SEQ+1))
  echo "[$LOG_SEQ][$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

debug_block() {
  echo "----- DEBUG ($1) -----"
  echo "$2"
  echo "----------------------"
}

step() {
  log "$1"
}

# ================= ENV =================
source "$ADE_BASE/ai_dev_env/config/env.sh"

INPUT="$1"
TASK="${@:2}"

PROJECT_PATH=$(realpath "$ADE_PROJECTS/$INPUT")
cd "$PROJECT_PATH"

log "🚀 Project: $(pwd)"

source .venv/bin/activate

MODELS_FILE="core/models.py"
ADMIN_FILE="core/admin.py"

MODEL_NAME=$(echo "$TASK" | grep -oP '(?<=Add ).*(?= model)' | awk '{print $1}')
CLASS_NAME=$(echo "$MODEL_NAME" | sed 's/.*/\u&/')

log "🎯 Target model: $CLASS_NAME"

# ================= CLEAN MODELS =================
clean_models() {
step "🧹 Cleaning models"

python - <<EOF
import re

file="$MODELS_FILE"

try:
    c=open(file).read()
except:
    c=""

# remove logs
c = re.sub(r'^\[\d+\].*$', '', c, flags=re.MULTILINE)

# remove separators
c = re.sub(r'-{5,}', '', c)

# remove markdown blocks
c = re.sub(r'```[\s\S]*?```', '', c)

imports="from django.db import models\n\n"

blocks=re.findall(r'class .*?models\.Model\):.*?(?=class|\Z)',c,re.S)

seen=set()
out=""

for b in blocks:
    name=re.findall(r'class (\w+)',b)[0]
    if name in seen:
        continue
    seen.add(name)
    out+=b.strip()+"\n\n"

open(file,"w").write(imports+out)
EOF

log "✅ Models cleaned"
}

# ================= CLEAN ADMIN =================
clean_admin() {
step "🧹 Cleaning admin"

python - <<EOF
import re

file="$ADMIN_FILE"

try:
    c=open(file).read()
except:
    c=""

# remove broken imports
c = re.sub(r'from \.models import .*', '', c)

# remove duplicates and empty lines
lines = list(dict.fromkeys([l for l in c.splitlines() if l.strip()]))

open(file,"w").write("\n".join(lines))
EOF

log "✅ Admin cleaned"
}

# ================= GENERATE =================
generate_model() {
MODEL=$1
RAW=$(echo "$MODEL" | sed 's|ollama/||')

step "🧠 Generating via $RAW"

OUTPUT=$(ollama run "$RAW" "
You are a Django expert.

Task: $TASK

Generate ONE Django model.

STRICT:
- Only one model class
- No imports
- No markdown
- No explanation
- Only Python class

Include:
- 4-6 meaningful fields
- created_at field
- __str__ method
")

if [ -z "$OUTPUT" ]; then
  log "❌ EMPTY OUTPUT"
  return 1
fi

debug_block "RAW OUTPUT" "$OUTPUT"

# ================= SAFE EXTRACTION =================
echo "$OUTPUT" | python - <<EOF
import sys,re

data=sys.stdin.read()

# remove markdown
data = re.sub(r'```[\s\S]*?```', '', data)

# remove logs
data = re.sub(r'^\[\d+\].*$', '', data, flags=re.MULTILINE)

# remove separators
data = re.sub(r'-{5,}', '', data)

# remove imports
data = re.sub(r'^from .*$', '', data, flags=re.MULTILINE)
data = re.sub(r'^import .*$', '', data, flags=re.MULTILINE)

match = re.search(r'class\s+\w+\(models\.Model\):[\s\S]+?(?=\nclass|\Z)', data)

if match:
    print(match.group(0).strip())
    exit(0)

print("")
exit(1)
EOF
}

# ================= INSERT =================
insert_model() {
printf "\n\n%s\n" "$1" >> "$MODELS_FILE"
log "🧱 Model inserted"
}

# ================= ADMIN =================
ensure_admin() {
step "🛠 Admin setup"

touch $ADMIN_FILE

grep -q "$CLASS_NAME" $ADMIN_FILE || {
cat <<EOF >> $ADMIN_FILE

from .models import $CLASS_NAME
admin.site.register($CLASS_NAME)
EOF
}
}

# ================= VALIDATE =================
validate() {
step "🧪 Django check"
python manage.py check
return $?
}

# ================= MAIN =================

clean_models
clean_admin

IFS=',' read -ra MODELS <<< "$ADE_MODELS_LOCAL"

SUCCESS=false

for MODEL in "${MODELS[@]}"; do

  log "🔁 Trying: $MODEL"

  CODE=$(generate_model "$MODEL")

  if [ -z "$CODE" ]; then
    log "❌ Generation failed"
    continue
  fi

  debug_block "$MODEL FINAL MODEL" "$CODE"

  insert_model "$CODE"

  clean_models
  clean_admin
  ensure_admin

  validate
  if [ $? -eq 0 ]; then
    log "🎉 SUCCESS with $MODEL"
    SUCCESS=true
    break
  else
    log "↩️ Rolling back"
    git checkout -- core/models.py
  fi

done

if [ "$SUCCESS" = false ]; then
  log "⚠️ Fallback model"

cat <<EOF >> "$MODELS_FILE"

class $CLASS_NAME(models.Model):
    name = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
EOF
fi

END_TIME=$(date +%s)
log "⏱ TOTAL TIME: $((END_TIME - START_TIME))s"
log "✅ Done"
