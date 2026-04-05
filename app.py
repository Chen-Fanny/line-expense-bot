from flask import Flask, request, abort, send_from_directory
from linebot import LineBotApi, WebhookHandler
from linebot.models import (
    MessageEvent,
    TextMessage,
    ImageMessage,
    TextSendMessage,
    ImageSendMessage,
    FollowEvent,
    RichMenu,
    RichMenuSize,
    RichMenuArea,
    RichMenuBounds,
    MessageAction
)
import os
import re
import json
import uuid
from collections import defaultdict
from datetime import datetime

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

app = Flask(__name__)

# =====================
# LINE 設定
# =====================
LINE_CHANNEL_ACCESS_TOKEN = "nw0V6TlwDsjHbyNKP4EmFcxfe6/2k88OKkbZXJJ0AjCqFm8CrMnTGPsC1X5sybGBYl9jDGvl3Si504alv2+a7922jh1NBLJUyyUMZ3cLkTH6LA5lxajNtGvZbRxhgp4aKPJhWfb0AjpZQpNUA9h/KQdB04t89/1O/w1cDnyilFU="
LINE_CHANNEL_SECRET = "7f40d057fb76ca704c476d12135a0c93"

line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)


# 這個一定要改成你自己的公開網址
# 例如 Render 部署後會像 https://your-app.onrender.com
BASE_URL = os.getenv("BASE_URL", "https://your-render-url.onrender.com")

line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)

# =====================
# 檔案設定
# =====================
DATA_FILE = "records.json"
IMAGE_DIR = "uploads"
CHART_DIR = "charts"

os.makedirs(IMAGE_DIR, exist_ok=True)
os.makedirs(CHART_DIR, exist_ok=True)

# 暫存資料
records = []

# =====================
# JSON 存讀
# =====================
def save_records():
    data_to_save = []
    for r in records:
        data_to_save.append({
            "user_id": r["user_id"],
            "item": r["item"],
            "amount": r["amount"],
            "category": r.get("category", "未分類"),
            "note": r.get("note", "無"),
            "image_path": r.get("image_path"),
            "time": r["time"].isoformat()
        })

    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data_to_save, f, ensure_ascii=False, indent=2)


def load_records():
    global records

    if not os.path.exists(DATA_FILE):
        records = []
        return

    with open(DATA_FILE, "r", encoding="utf-8") as f:
        raw_data = json.load(f)

    records = []
    for r in raw_data:
        records.append({
            "user_id": r["user_id"],
            "item": r["item"],
            "amount": r["amount"],
            "category": r.get("category", "未分類"),
            "note": r.get("note", "無"),
            "image_path": r.get("image_path"),
            "time": datetime.fromisoformat(r["time"])
        })

# =====================
# 說明文字
# =====================
def get_welcome_text():
    return (
        "🐮💗 大家好我是Fan做的食帳助手！歐耶\n\n"
        "你可以這樣用我👇\n\n"
        "📌 記帳\n"
        "輸入格式：項目 金額 / 分類 / 備註\n"
        "例如：三明治 100 / 午餐 / 7-11\n\n"
        "📊 查詢\n"
        "(1) 今天 → 查看今天支出\n"
        "(2) 本月 → 查看本月總支出\n"
        "(3) 統計 → 文字統計 + 圓餅圖\n"
        "(4) 統計長條 → 文字統計 + 長條圖\n\n"
        "🗑️ 刪除\n"
        "(1) 刪除最後一筆\n"
        "(2) 刪除今天\n\n"
        "📷 照片\n"
        "記帳後可直接上傳照片\n"
        "我會幫你附加到最近一筆紀錄\n\n"
        "🌟 說明\n"
        "輸入：help 或 說明\n\n"
        "👇 也可以用下面選單操作喔！"
        

    )

# =====================
# 圖表圖片路由
# =====================
@app.route("/charts/<filename>")
def serve_chart(filename):
    return send_from_directory(CHART_DIR, filename)

# =====================
# Webhook
# =====================
@app.route("/callback", methods=["POST"])
def callback():
    signature = request.headers.get("X-Line-Signature", "")
    body = request.get_data(as_text=True)

    try:
        handler.handle(body, signature)
    except Exception as e:
        print("error:", e)
        abort(400)

    return "OK", 200

# =====================
# 畫圖函式
# =====================
def generate_pie_chart(user_records):
    category_sum = defaultdict(int)

    for r in user_records:
        category = r.get("category", "未分類")
        category_sum[category] += r["amount"]

    if not category_sum:
        return None

    labels = list(category_sum.keys())
    sizes = list(category_sum.values())

    filename = f"{uuid.uuid4().hex}_pie.png"
    filepath = os.path.join(CHART_DIR, filename)

    plt.figure(figsize=(8, 8))
    plt.pie(sizes, labels=labels, autopct="%1.1f%%")
    plt.title("Expense Category Ratio")
    plt.tight_layout()
    plt.savefig(filepath)
    plt.close()

    return filename


def generate_bar_chart(user_records):
    category_sum = defaultdict(int)

    for r in user_records:
        category = r.get("category", "未分類")
        category_sum[category] += r["amount"]

    if not category_sum:
        return None

    labels = list(category_sum.keys())
    values = list(category_sum.values())

    filename = f"{uuid.uuid4().hex}_bar.png"
    filepath = os.path.join(CHART_DIR, filename)

    plt.figure(figsize=(10, 6))
    plt.bar(labels, values)
    plt.title("Expense by Category")
    plt.xlabel("Category")
    plt.ylabel("Amount")
    plt.tight_layout()
    plt.savefig(filepath)
    plt.close()

    return filename

# =====================
# 加好友歡迎
# =====================
@handler.add(FollowEvent)
def handle_follow(event):
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=get_welcome_text())
    )

# =====================
# 上傳圖片：綁到最近一筆記帳
# =====================
@handler.add(MessageEvent, message=ImageMessage)
def handle_image(event):
    user_id = event.source.user_id

    user_records = [r for r in records if r["user_id"] == user_id]

    if not user_records:
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text="請先輸入一筆記帳再上傳照片!!!")
        )
        return

    last_record = user_records[-1]
    message_content = line_bot_api.get_message_content(event.message.id)

    filename = f"{user_id}_{event.message.id}.jpg"
    filepath = os.path.join(IMAGE_DIR, filename)

    with open(filepath, "wb") as f:
        for chunk in message_content.iter_content():
            f.write(chunk)

    last_record["image_path"] = filepath
    save_records()

    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(
            text=(
                f"📷🌟 照片上傳成功！\n"
                f"已加到最近一筆記帳：\n"
                f"項目：{last_record['item']}\n"
                f"金額：{last_record['amount']} 元"
            )
        )
    )

# =====================
# 文字訊息處理
# =====================
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    text = event.message.text.strip()
    user_id = event.source.user_id

    # 說明
    if text in ["help", "說明", "指令"]:
        reply = get_welcome_text()
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply))
        return

    # 記一筆提示
    elif text == "記一筆":
        reply = (
            "請輸入：項目 金額 / 分類 / 備註\n"
            "例如：三明治 100 / 午餐 / 7-11\n\n"
            "也可以簡化輸入：\n"
            "三明治 100\n"
            "三明治 100 / 午餐\n\n"
            "❣️ 記帳完成後也可以直接傳照片記錄喔"
        )
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply))
        return

    # 今天
    elif text == "今天":
        today = datetime.now().date()
        today_records = [
            r for r in records
            if r["user_id"] == user_id and r["time"].date() == today
        ]

        if not today_records:
            reply = "你今天還沒有記帳!快點🙁"
        else:
            total = sum(r["amount"] for r in today_records)
            lines = []
            for i, r in enumerate(today_records):
                photo_mark = " 📷" if r.get("image_path") else ""
                lines.append(
                    f"{i + 1}. {r['item']} {r['amount']}元｜{r.get('category', '未分類')}｜{r.get('note', '無')}{photo_mark}"
                )

            reply = "📅 今天支出\n" + "\n".join(lines) + f"\n\n合計：{total} 元"

        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply))
        return

    # 本月
    elif text == "本月":
        now = datetime.now()
        month_records = [
            r for r in records
            if r["user_id"] == user_id
            and r["time"].year == now.year
            and r["time"].month == now.month
        ]

        if not month_records:
            reply = "你這個月還沒有記帳!快點🙁"
        else:
            total = sum(r["amount"] for r in month_records)
            photo_count = sum(1 for r in month_records if r.get("image_path"))
            reply = (
                f"📊 本月總支出：{total} 元\n"
                f"共有 {len(month_records)} 筆紀錄\n"
                f"其中有 {photo_count} 筆附照片"
            )

        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply))
        return

    # 統計：圓餅圖
    elif text == "統計":
        user_records = [r for r in records if r["user_id"] == user_id]

        if not user_records:
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text="目前還沒有資料可以統計🙁")
            )
            return

        total = sum(r["amount"] for r in user_records)
        photo_count = sum(1 for r in user_records if r.get("image_path"))
        chart_filename = generate_pie_chart(user_records)

        if not chart_filename:
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text="無法產生圖表🙁")
            )
            return

        image_url = f"{BASE_URL}/charts/{chart_filename}"

        line_bot_api.reply_message(
            event.reply_token,
            [
                TextSendMessage(
                    text=(
                        f"📈 總統計\n"
                        f"總筆數：{len(user_records)}\n"
                        f"總金額：{total} 元\n"
                        f"附照片筆數：{photo_count}"
                    )
                ),
                ImageSendMessage(
                    original_content_url=image_url,
                    preview_image_url=image_url
                )
            ]
        )
        return

    # 統計：長條圖
    elif text == "統計長條":
        user_records = [r for r in records if r["user_id"] == user_id]

        if not user_records:
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text="目前還沒有資料可以統計🙁")
            )
            return

        total = sum(r["amount"] for r in user_records)
        photo_count = sum(1 for r in user_records if r.get("image_path"))
        chart_filename = generate_bar_chart(user_records)

        if not chart_filename:
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text="無法產生圖表🙁")
            )
            return

        image_url = f"{BASE_URL}/charts/{chart_filename}"

        line_bot_api.reply_message(
            event.reply_token,
            [
                TextSendMessage(
                    text=(
                        f"📊 長條統計\n"
                        f"總筆數：{len(user_records)}\n"
                        f"總金額：{total} 元\n"
                        f"附照片筆數：{photo_count}"
                    )
                ),
                ImageSendMessage(
                    original_content_url=image_url,
                    preview_image_url=image_url
                )
            ]
        )
        return

    # 刪除最後一筆
    elif text == "刪除最後一筆":
        user_records = [r for r in records if r["user_id"] == user_id]

        if not user_records:
            reply = "目前沒有可以刪除的紀錄"
        else:
            last_record = user_records[-1]
            records.remove(last_record)
            save_records()

            reply = (
                f"🗑️ 已刪除最後一筆紀錄\n"
                f"項目：{last_record['item']}\n"
                f"金額：{last_record['amount']} 元\n"
                f"分類：{last_record.get('category', '未分類')}\n"
                f"備註：{last_record.get('note', '無')}"
            )

        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply))
        return

    # 刪除今天全部
    elif text == "刪除今天":
        today = datetime.now().date()
        today_records = [
            r for r in records
            if r["user_id"] == user_id and r["time"].date() == today
        ]

        if not today_records:
            reply = "今天沒有紀錄可以刪除"
        else:
            count = len(today_records)
            total = sum(r["amount"] for r in today_records)

            records[:] = [
                r for r in records
                if not (r["user_id"] == user_id and r["time"].date() == today)
            ]
            save_records()

            reply = f"🗑️ 已刪除今天的 {count} 筆紀錄，共 {total} 元"

        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply))
        return

    # 記帳輸入
    else:
        match = re.match(r"(.+?)\s+(\d+)(?:\s*/\s*(.+))?$", text)

        if match:
            item = match.group(1).strip()
            amount = int(match.group(2))
            extra = match.group(3)

            category = "未分類"
            note = "無"

            if extra:
                parts = [p.strip() for p in extra.split("/")]

                if len(parts) >= 1 and parts[0]:
                    category = parts[0]
                if len(parts) >= 2 and parts[1]:
                    note = parts[1]

            records.append({
                "user_id": user_id,
                "item": item,
                "amount": amount,
                "category": category,
                "note": note,
                "image_path": None,
                "time": datetime.now()
            })
            save_records()

            reply = (
                f"✅ 記帳成功\n"
                f"項目：{item}\n"
                f"金額：{amount} 元\n"
                f"分類：{category}\n"
                f"備註：{note}"
            )
        else:
            reply = (
                "看不懂這個指令 😵\n"
                "你可以輸入：\n"
                "1. 三明治 100\n"
                "2. 三明治 100 / 午餐\n"
                "3. 三明治 100 / 午餐 / 7-11\n"
                "4. 今天\n"
                "5. 本月\n"
                "6. 統計\n"
                "7. 統計長條\n"
                "8. 刪除最後一筆\n"
                "9. 刪除今天\n"
                "10. help"
            )

        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply))
        return

# =====================
# Rich Menu
# =====================
def create_rich_menu():
    rich_menu = RichMenu(
        size=RichMenuSize(width=2500, height=1686),
        selected=True,
        name="menu",
        chat_bar_text="選單",
        areas=[
            RichMenuArea(
                bounds=RichMenuBounds(x=0, y=0, width=1250, height=1686),
                action=MessageAction(text="記一筆")
            ),
            RichMenuArea(
                bounds=RichMenuBounds(x=1250, y=0, width=1250, height=562),
                action=MessageAction(text="今天")
            ),
            RichMenuArea(
                bounds=RichMenuBounds(x=1250, y=562, width=1250, height=562),
                action=MessageAction(text="本月")
            ),
            RichMenuArea(
                bounds=RichMenuBounds(x=1250, y=1124, width=1250, height=562),
                action=MessageAction(text="統計")
            )
        ]
    )

    rich_menu_id = line_bot_api.create_rich_menu(rich_menu)
    print("Rich Menu ID:", rich_menu_id)

    with open("background.jpg", "rb") as f:
        line_bot_api.set_rich_menu_image(rich_menu_id, "image/jpeg", f)

    line_bot_api.set_default_rich_menu(rich_menu_id)

# =====================
# 主程式
# =====================
if __name__ == "__main__":
    load_records()
    # create_rich_menu()   # 要重建選單時再打開
    app.run(host="0.0.0.0", port=5000)