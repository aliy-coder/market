from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, MessageHandler, Filters
import os

import methods
from database import Database
from register import check
from messages import message_handler, photo_handler, admin_add_product_start, admin_flow_handler, admin_delete_product, admin_accept_order, admin_reject_order
from inlines import inline_handler
import globals

ADMIN_ID = 1482897133
TOKEN = os.getenv("BOT_TOKEN")

db = Database("db-evos.db")


def start_handler(update, context):
    check(update, context)


def contact_handler(update, context):
    message = update.message.contact.phone_number
    user = update.message.from_user
    db.update_user_data(user.id, "phone_number",message)
    check(update,context)

# location_handler remains unchanged (uses context.user_data for receipts)
from database import Database as DB

def location_handler(update, context):
    db_user = db.get_user_by_chat_id(update.message.from_user.id)
    location = update.message.location
    payment_type = context.user_data.get("payment_type", None)
    last_order = db.create_order(db_user['id'], context.user_data.get("carts", {}), payment_type, location)

    receipt_file_id = context.user_data.get("receipt_file_id")
    card_number = context.user_data.get("card_number_used")
    if receipt_file_id:
        db.add_order_payment(last_order, payment_type, card_number=card_number, receipt_file_id=receipt_file_id)
        # forward to admin
        total_price = 0
        carts = context.user_data.get("carts", {})
        lang_code = globals.LANGUAGE_CODE[db_user['lang_id']]
        text = ""
        for cart, val in carts.items():
            product = db.get_product_for_cart(int(cart))
            text += f"{val} x {product[f'cat_name_{lang_code}']} {product[f'name_{lang_code}']}\n"
            total_price += product['price'] * val
        caption = f"<b>Yangi buyurtma (karta to'lov):</b>\n\n" \
                  f"👤 <b>Ism-familiya:</b> {db_user['first_name']} {db_user['last_name']}\n" \
                  f"📞 <b>Telefon raqam:</b> {db_user['phone_number']} \n\n" \
                  f"📥 <b>Buyurtma:</b>\n{text}\n" \
                  f"📌 Umumiy: {total_price} {globals.SUM[db_user['lang_id']]}\n" \
                  f"💳 Kart raqami: {card_number if card_number else '—'}"
        context.bot.send_photo(chat_id=ADMIN_ID, photo=receipt_file_id, caption=caption, parse_mode='HTML')
    else:
        if context.user_data.get("carts", {}):
            carts = context.user_data.get("carts")
            text = "\n"
            lang_code = globals.LANGUAGE_CODE[db_user['lang_id']]
            total_price = 0
            for cart, val in carts.items():
                product = db.get_product_for_cart(int(cart))
                text += f"{val} x {product[f'cat_name_{lang_code}']} {product[f'name_{lang_code}']}\n"
                total_price += product['price'] * val

            text += f"\n{globals.ALL[db_user['lang_id']]}: {total_price} {globals.SUM[db_user['lang_id']]}"

        context.bot.send_message(
            chat_id=ADMIN_ID,
            text=f"<b>Yangi buyurtma:</b>\n\n"
                 f"👤 <b>Ism-familiya:</b> {db_user['first_name']} {db_user['last_name']}\n"
                 f"📞 <b>Telefon raqam:</b> {db_user['phone_number']} \n\n"
                 f"📥 <b>Buyurtma:</b> \n"
                 f"{text}",
            parse_mode='HTML'
        )

    context.bot.send_location(
        chat_id=ADMIN_ID,
        latitude=float(location.latitude),
        longitude=float(location.longitude)
    )
    methods.send_main_menu(context, update.message.from_user.id, db_user['lang_id'])


def main():
    updater = Updater(TOKEN)
    dispatcher = updater.dispatcher

    dispatcher.add_handler(CommandHandler('start', start_handler))
    dispatcher.add_handler(MessageHandler(Filters.text, message_handler))
    dispatcher.add_handler(MessageHandler(Filters.contact, contact_handler))
    dispatcher.add_handler(CallbackQueryHandler(inline_handler))
    dispatcher.add_handler(MessageHandler(Filters.location, location_handler))
    dispatcher.add_handler(MessageHandler(Filters.photo, photo_handler))

    # admin commands
    dispatcher.add_handler(CommandHandler('add_product', admin_add_product_start))
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, admin_flow_handler))
    dispatcher.add_handler(CommandHandler('del_product', admin_delete_product))
    dispatcher.add_handler(CommandHandler('accept_order', admin_accept_order))
    dispatcher.add_handler(CommandHandler('reject_order', admin_reject_order))

    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()
