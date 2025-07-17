from flask import Flask, render_template, request, jsonify
import boto3
import pymysql
import logging
from retrying import retry

app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# AWS region
AWS_REGION = 'us-east-1'

# Parameter Store’dan kullanıcı adı ve şifreyi okuyan fonksiyon
def get_parameter(name):
    try:
        ssm = boto3.client('ssm', region_name=AWS_REGION)
        response = ssm.get_parameter(Name=name, WithDecryption=True)
        return response['Parameter']['Value']
    except Exception as e:
        logger.error(f"Failed to retrieve SSM parameter {name}: {e}")
        raise

# DB bilgilerini Parameter Store’dan al
try:
    DB_HOST = 'roman-db.c5i6e2kemznc.us-east-1.rds.amazonaws.com'
    DB_USER = get_parameter('/sql/username')
    DB_PASS = get_parameter('/sql/password')
    DB_NAME = 'roman_db'
except Exception as e:
    logger.error(f"Failed to initialize DB credentials: {e}")
    raise

# DB bağlantısı için fonksiyon
@retry(stop_max_attempt_number=3, wait_fixed=2000)
def get_db_connection():
    try:
        return pymysql.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASS,
            db=DB_NAME,
            cursorclass=pymysql.cursors.DictCursor,
            connect_timeout=5
        )
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        raise

# Veritabanına kayıt ekleme fonksiyonu
def save_conversion(decimal_num, roman_num):
    connection = None
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
        logger.info(f"Saved conversion: {decimal_num} -> {roman_num}")
    except Exception as e:
        logger.error(f"Error saving to database: {e}")
        raise
    finally:
        if connection:
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
    try:
        if request.method == 'POST':
            alpha = request.form.get('number')
            if not alpha or not alpha.isdecimal():
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
    except Exception as e:
        logger.error(f"Error in main_post: {e}")
        return jsonify({"error": "Internal Server Error"}), 500

@app.route('/health', methods=['GET'])
def health_check():
    try:
        connection = get_db_connection()
        connection.close()
        return jsonify({"status": "healthy", "database": "connected"}), 200
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return jsonify({"status": "unhealthy", "error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)