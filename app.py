from flask import Flask, jsonify, request
import os
From flask_cors import CORS

'''
Notes:
Probably generate an error somewhere
Potential file_send() error at line 26
Make sure files are in correct convention
Need update website
Make sure the code can acess the pdfs
'''

app = Flask(__name__)
CORS(app) 
flag=set([])


#sends pdf
@app.route("/api/get_pdf", methods=['GET'])
def send_data():
	#for baseurl/api/get?date=YYYY-MM-DD
  date=request.args()
  for temp in os.listdir(): #Finding the file path
    if(date in temp):
      return send_file(temp)
  flag.add(date) #debug
  return 404


#initializes the website(mainly for debug)
@app.route("/")
def hello_world():
    hello_api()
    return "<p>Hello, World!</p>"


#Handles potential post requests
@app.route("/api/post", methods=['POST'])
def recieve_data():
	if(request.is_json):
		data=request.get_json()
		return {"error":"Data Recieved"},200
	return {"error":"Non-valid format"},400


#Gives website valid dates
@app.route("/api/get_dates", methods=['GET'])
def send_data():
	date_ls=[]
	#for baseurl/api/get_dates
  for date in os.listdir():
    if("SMM" in date):
      cnt=date[3:] #isolating the date format
      date_ls.append(cnt[:-4])
	if(len(date_ls)<1):
		return 404
  dates=jsonify({"dates":set(date_ls)})
  return dates
 
if __name__ == '__main__':
    app.run()
