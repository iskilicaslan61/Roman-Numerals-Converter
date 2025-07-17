from flask import Flask, render_template, request
import pymysql
import boto3
import json
from botocore.exceptions import ClientError

app = Flask(__name__)

# Hardcoded values
RDS_HOST = 'roman-db.c5i6e2kemznc.us-east-1.rds.amazonaws.com'
DB_NAME = 'roman_db'

# Only get username and password from Secrets Manager
def get_db_credentials(secret_name, region_name='us-east-1'):
    session = boto3.session.Session()
    client = session.client(service_name='secretsmanager', region_name=region_name)
    try:
        response = client.get_secret_value(SecretId=secret_name)
    except ClientError as e:
        raise e
    return json.loads(response['SecretString'])

# Fetch credentials from secret
creds = get_db_credentials("my-rds-secret")  # change to your actual secret name

# Connect to RDS
db = pymysql.connect(
    host=RDS_HOST,
    user=creds['username'],
    password=creds['password'],
    database=DB_NAME
)

def convert(decimal_num):
    roman = {
        1000:'M', 900:'CM', 500:'D', 400:'CD',
        100:'C', 90:'XC', 50:'L', 40:'XL',
        10:'X', 9:'IX', 5:'V', 4:'IV', 1:'I'
    }
    num_to_roman = ''
    for i in roman:
        num_to_roman += roman[i] * (decimal_num // i)
        decimal_num %= i
    return num_to_roman

@app.route('/', methods=['POST', 'GET'])
def main_post():
    if request.method == 'POST':
        alpha = request.form['number']
        if not alpha.isdecimal():
            return render_template('index.html', developer_name='Ismail Kilicaslan', not_valid=True)
        number = int(alpha)
        if not 0 < number < 4000:
            return render_template('index.html', developer_name='Ismail Kilicaslan', not_valid=True)

        roman_value = convert(number)

        try:
            cursor = db.cursor()
            insert_query = "INSERT INTO conversions (decimal_number, roman_number) VALUES (%s, %s)"
            cursor.execute(insert_query, (number, roman_value))
            db.commit()
        except Exception as e:
            print("DB Error:", e)

        return render_template('result.html', number_decimal=number, number_roman=roman_value, developer_name='Ismail Kilicaslan')
    else:
        return render_template('index.html', developer_name='Ismail Kilicaslan', not_valid=False)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
