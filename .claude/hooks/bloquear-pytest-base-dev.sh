#!/bin/sh
# PreToolUse (Bash): la suite hace drop_all al empezar, así que correrla contra la base de
# desarrollo `taekwondo` la borra. Bloquea pytest con una DATABASE_URL a esa base exacta.
input=$(cat)

if printf '%s' "$input" | grep -q 'pytest' &&
   printf '%s' "$input" | grep -Eq '5432/taekwondo([^_[:alnum:]-]|$)'; then
  echo "Bloqueado: pytest contra la base 'taekwondo' (desarrollo) la borra. Usar 'taekwondo_test' (ver README.md, sección Docker)." >&2
  exit 2
fi
