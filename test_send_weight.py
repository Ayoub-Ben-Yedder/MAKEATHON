import requests

#url = "http://10.97.193.192:5000/api/weight"
url = "http://10.97.193.40:8765/pick"
data = {
    "product": "A",
    "x": 6,
    "y": 5
}

response = requests.post(url, json=data)

print("Status:", response.status_code)
print("Response:", response.text)