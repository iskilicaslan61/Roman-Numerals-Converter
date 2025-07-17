from flask import Flask, render_template, request
import boto3
import pymysql

app = Flask(__name__)

# AWS region
AWS_REGION = 'us-east-1'

# Parameter Store'dan kullanıcı adı ve şifreyi okuyan fonksiyon
def get_parameter(name):
    ssm = boto3.client('ssm', region_name=AWS_REGION)
    response = ssm.get_parameter(Name=name, WithDecryption=True)
    return response['Parameter']['Value']

# DB bilgilerini Parameter Store'dan al
DB_HOST = 'roman-db.c5i6e2kemznc.us-east-1.rds.amazonaws.com'
DB_USER = get_parameter('/sql/username')
DB_PASS = get_parameter('/sql/password')
DB_NAME = 'roman_db'

# DB bağlantısı için fonksiyon
def get_db_connection():
    return pymysql.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASS,
        db=DB_NAME,
        cursorclass=pymysql.cursors.DictCursor
    )

# Veritabanına kayıt ekleme fonksiyonu
def save_conversion(decimal_num, roman_num):
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            # Tablo yoksa oluştur
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS conversions (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    decimal_number INT NOT NULL,
                    roman_number VARCHAR(20) NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            # Kayıt ekle
            sql = "INSERT INTO conversions (decimal_number, roman_number) VALUES (%s, %s)"
            cursor.execute(sql, (decimal_num, roman_num))
        connection.commit()
    except Exception as e:
        print(f"Error saving to database: {e}")
    finally:
        connection.close()

def convert(decimal_num):
    roman = {
        1000:'M', 900:'CM', 500:'D', 400:'CD',
        100:'C', 90:'XC', 50:'L', 40:'XL',
        10:'X', 9:'IX', 5:'V', 4:'IV', 1:'I'
    }
    num_to_roman = ''
    for i in roman.keys():
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
        
        # Sayıyı Roma rakamına çevir
        roman_result = convert(number)
        # Veritabanına kaydet
        save_conversion(number, roman_result)
        
        return render_template('result.html', number_decimal=number, number_roman=roman_result, developer_name='Ismail Kilicaslan')
    else:
        return render_template('index.html', developer_name='Ismail Kilicaslan', not_valid=False)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)