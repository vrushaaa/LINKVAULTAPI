#!/bin/bash
set -e

BASE_URL="http://127.0.0.1:5000"
COOKIE_JAR="cookies.txt"

echo "🧪 Starting LinkVault API tests..."

rm -f $COOKIE_JAR

# Signup (idempotent – can return 201 or 400 if user exists)
curl -s -o /dev/null -w "%{http_code}" -X POST "$BASE_URL/signup" \
  -H "Content-Type: application/json" \
  -d '{"name":"Test User","email":"testuser@example.com","username":"testuser123","password":"password123"}' || true

# Login and save cookies
LOGIN_STATUS=$(curl -s -o /dev/null -w "%{http_code}" -c $COOKIE_JAR \
  -X POST "$BASE_URL/login" \
  -H "Content-Type: application/json" \
  -d '{"username":"testuser123","password":"password123"}')

if [ "$LOGIN_STATUS" -ne 200 ]; then
  echo "❌ Login failed (status $LOGIN_STATUS)"
  exit 1
fi
echo "✅ Login OK"

# Create bookmark
CREATE_RESPONSE=$(curl -s -b $COOKIE_JAR -X POST "$BASE_URL/api/bookmarks" \
  -H "Content-Type: application/json" \
  -d '{"url":"https://example.com","title":"Example Site","tags":["ci-test"]}')

BOOKMARK_ID=$(echo "$CREATE_RESPONSE" | grep -o '"id":[0-9]*' | cut -d':' -f2 || true)

if [ -z "$BOOKMARK_ID" ]; then
  echo "❌ Create bookmark failed"
  echo "$CREATE_RESPONSE"
  exit 1
fi
echo "✅ Created bookmark id=$BOOKMARK_ID"

# Get bookmark
curl -f -s -b $COOKIE_JAR "$BASE_URL/api/bookmarks/$BOOKMARK_ID" > /dev/null
echo "✅ GET bookmark OK"

# List bookmarks
curl -f -s -b $COOKIE_JAR "$BASE_URL/api/bookmarks" > /dev/null
echo "✅ List bookmarks OK"

# Update
curl -f -s -b $COOKIE_JAR -X PUT "$BASE_URL/api/bookmarks/$BOOKMARK_ID" \
  -H "Content-Type: application/json" \
  -d '{"title":"Updated Title"}' > /dev/null
echo "✅ Update bookmark OK"

# Toggle archive
curl -f -s -b $COOKIE_JAR -X PATCH "$BASE_URL/api/bookmarks/$BOOKMARK_ID/archive" > /dev/null
echo "✅ Toggle archive OK"

# Delete
curl -f -s -b $COOKIE_JAR -X DELETE "$BASE_URL/api/bookmarks/$BOOKMARK_ID" > /dev/null
echo "✅ Delete bookmark OK"

echo "🎉 ALL API TESTS PASSED!"
exit 0
