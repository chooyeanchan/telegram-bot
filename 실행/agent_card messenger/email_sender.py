"""
Gmail SMTP를 통한 명함 이메일 발송
"""
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from dotenv import load_dotenv

load_dotenv()


def send_my_card(to_email: str, recipient_name: str = ""):
    """명함 소유자에게 내 명함 이미지와 소개 문구를 이메일로 발송합니다."""
    gmail_address = os.getenv("GMAIL_ADDRESS")
    gmail_password = os.getenv("GMAIL_APP_PASSWORD")
    card_image_path = os.getenv("MY_CARD_IMAGE_PATH", "my_card.jpg")
    intro_template = os.getenv(
        "MY_EMAIL_INTRO",
        "안녕하세요! 오늘 명함을 교환했습니다. 제 명함을 첨부 드립니다."
    )

    if not gmail_address or not gmail_password:
        raise ValueError("GMAIL_ADDRESS 또는 GMAIL_APP_PASSWORD가 설정되지 않았습니다.")

    # 소개 문구에서 줄바꿈 처리
    intro_text = intro_template.replace("\\n", "\n")

    msg = MIMEMultipart()
    msg["From"] = gmail_address
    msg["To"] = to_email
    msg["Subject"] = "명함을 전달 드립니다"

    body = MIMEText(intro_text, "plain", "utf-8")
    msg.attach(body)

    # 명함 이미지 첨부
    if os.path.exists(card_image_path):
        with open(card_image_path, "rb") as f:
            img_data = f.read()
        image = MIMEImage(img_data, name=os.path.basename(card_image_path))
        msg.attach(image)

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(gmail_address, gmail_password)
        server.sendmail(gmail_address, to_email, msg.as_string())
