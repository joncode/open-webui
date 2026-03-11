#!/bin/bash
# Update PersistentConfig values in the DB config table.
# These override .env/configmap values at runtime.
#
# Usage:
#   On staging: ./update-db-config.sh staging
#   On prod:    ./update-db-config.sh prod
#
# Run from inside a pod or with psql access to the jaco DB.
# Alternatively, pipe through kubectl exec:
#   kubectl -n jaco-stg exec -i deployment/jaco -- python -c "..."

set -euo pipefail

ENV="${1:-staging}"

if [ "$ENV" = "staging" ]; then
  NS="jaco-stg"
elif [ "$ENV" = "prod" ]; then
  NS="jaco"
else
  echo "Usage: $0 [staging|prod]"
  exit 1
fi

echo "==> Updating DB config for $ENV (namespace: $NS)..."

# Update default model + ensure version check is disabled + enable openai api
sudo kubectl -n "$NS" exec -i deployment/jaco -- python3 -c "
import json
from open_webui.internal.db import get_db
from sqlalchemy import text

with get_db() as db:
    row = db.execute(text(\"SELECT data FROM config LIMIT 1\")).fetchone()
    if row:
        data = json.loads(row[0]) if isinstance(row[0], str) else row[0]

        # Set default model
        data.setdefault('ui', {})
        data['ui']['default_models'] = 'venice-uncensored'
        data['ui']['enable_community_sharing'] = False
        data['ui']['enable_message_rating'] = False
        data['ui']['prompt_suggestions'] = []

        # Ensure OpenAI API is enabled
        data.setdefault('openai', {})
        data['openai']['enable'] = True

        # Disable evaluation arena
        data.setdefault('evaluation', {})
        data['evaluation'].setdefault('arena', {})
        data['evaluation']['arena']['enable'] = False

        data.setdefault('general', {})

        db.execute(
            text(\"UPDATE config SET data = :data\"),
            {'data': json.dumps(data)}
        )
        db.commit()
        print('Config updated successfully')
        print(json.dumps(data, indent=2))
    else:
        print('No config row found — first boot will create it from env')
"

echo "==> Done. Restart deployment to pick up changes:"
echo "    sudo kubectl -n $NS rollout restart deployment/jaco"
