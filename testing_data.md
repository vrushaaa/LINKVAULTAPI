# post data
{
  "url": "https://aws.com",
  "title": "AWS-amazon web services",
  "notes": "cloud based platform for computing resources",
  "tags": ["cloud", "amazon"],
  "archived": false,
}

# get by id
http://127.0.0.1:5000/api/bookmarks/11

# get all
http://127.0.0.1:5000/api/bookmarks

# updates
http://127.0.0.1:5000/api/bookmarks/11
{
  "tags": ["cloud", "amazon","web-service"]
}

#serch by tag
http://127.0.0.1:5000/api/bookmarks?tags=Python

# archive status
http://127.0.0.1:5000/api/bookmarks/11/archive

# delete

http://127.0.0.1:5000/api/bookmarks/11




# cli
# create
python linkvault_client.py create "https://www.geeksforgeeks.org/python/python-projects-beginner-to-advanced/" --title "python projects" --tags projects,python,geeksforgeeks

# update
python linkvault_client.py update 11 --tags projects,python,geeksforgeeks,learning

# list
python linkvault_client.py list
# filter by tags
python linkvault_client.py list --tag python
# filter by page
python linkvault_client.py list --page 2
# filter by keyword
python linkvault_client.py list --q projects 
# filter by archive status
python linkvault_client.py list --archived

# toggle-archive
python linkvault_client.py toggle-archive 7

# delete
python linkvault_client.py delete 11

# export
python linkvault_client.py export my_bookmarks.html

start my_bookmarks.html 



<!-- Document which states functionalities of project -->


python linkvault_client.py signup --name "Test User" --email "test@gmail.com" --username testcli --password test123
python linkvault_client.py login --username testcli --password test123
python linkvault_client.py create "https://example.com" --title "Example"
python linkvault_client.py create "https://google.com" --tags search,tech
python linkvault_client.py list --format-json
python linkvault_client.py update 1 --notes "Updated note"
python linkvault_client.py get 1 --format-json
python linkvault_client.py qr 1
python linkvault_client.py export bookmarks.html
python linkvault_client.py delete 1
python linkvault_client.py logout
