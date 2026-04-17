#!/bin/bash

PROJECT=$1
BASE="$ADE_PROJECTS/$PROJECT"

code "$BASE" &
runai "$PROJECT"
