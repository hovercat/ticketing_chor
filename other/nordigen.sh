# get access and refresh tokens
curl -X POST "https://ob.nordigen.com/api/v2/token/new/" \                                                                                              ✔  base  
    -H 'accept: application/json' \
    -H 'Content-Type: application/json' \
    -d "{
        \"secret_id\": \"$SECRET_ID\",
        \"secret_key\": \"$SECRET_KEY\"
    }"




# when access token expires, refresh using refresh token
curl -X POST "https://ob.nordigen.com/api/v2/token/refresh/" \
    -H 'accept: application/json' \
    -H 'Content-Type: application/json' \
    -d '{
        "refresh": "$REFRESH_TOKEN"
    }'

# provide access token in auth header
curl -X GET "https://ob.nordigen.com/api/v2/agreements/enduser/{id}/"
    -H  'accept: application/json'
    -H  "Authorization: Bearer $ACCESS_TOKEN"
            
            
# find my bank:
curl -X GET "https://ob.nordigen.com/api/v2/institutions/?country=at"  \
-H  "accept: application/json" \
-H  "Authorization: Bearer $ACCESS_TOKEN"


# define end user agreement
curl -X POST "https://ob.nordigen.com/api/v2/agreements/enduser/" -H  "accept: application/json" -H  "Content-Type: application/json" -H  "Authorization: Bearer $ACCESS_TOKEN" -d "{  
       \"institution_id\": \"$INST_ID_RAIFFEISEN\", 
       \"max_historical_days\": \"5\", 
       \"access_valid_for_days\": \"10\", 
       \"access_scope\": [\"transactions\"]
       }"
# response:


# build a link between both
curl -X POST "https://ob.nordigen.com/api/v2/requisitions/" -H  "accept: application/json" -H  "Content-Type: application/json" -H  "Authorization: Bearer $ACCESS_TOKEN" -d "{  
      \"redirect\": \"http://www.yourwebpage.com\", 
      \"institution_id\": \"$INST_ID_RAIFFEISEN\",
      \"agreement\": \"$EUA\", 
      \"user_language\":\"DE\" }"
      

# list linked bank accounts
curl -X GET "https://ob.nordigen.com/api/v2/requisitions/$LINK_ID/" -H  "accept: application/json" -H  "Authorization: Bearer $ACCESS_TOKEN" 

curl -X GET "https://ob.nordigen.com/api/v2/accounts/$BANK_ACC_ID/transactions" -H  "accept: application/json" -H  "Authorization: Bearer $ACCESS_TOKEN" 


