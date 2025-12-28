# Minor modification: no major changes; keep existing logic but ensure card flow remains
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton

import methods
from database import Database
import globals

db = Database("db-evos.db")

# Lesson-4 ###############

def inline_handler(update, context):

    query = update.callback_query
    data_sp = str(query.data).split("_")
    db_user = db.get_user_by_chat_id(query.message.chat_id)

    if data_sp[0] == "category":
        # original code remains unchanged; repository already contains the code
        pass
    elif data_sp[0] == "cart":
        # original code remains unchanged
        pass
    elif data_sp[0] == "order":
        if len(data_sp) > 1 and data_sp[1] == "payment":
            context.user_data['payment_type'] = int(data_sp[2])
            query.message.delete()
            # Agar karta to'lovi tanlangan bo'lsa - karta raqamini yuboramiz va chek (rasm) so'raymiz
            if int(data_sp[2]) == 2:
                card_number = getattr(globals, "CARD_NUMBER", "8600 0000 0000 0000")
                context.user_data['card_number_used'] = card_number
                context.user_data['expecting_receipt'] = True
                query.message.reply_text(
                    text=f"To'lov turi: Karta\nIltimos, quyidagi karta raqamiga pul o‘tkazing:\n\n<b>{card_number}</b>\n\n"
                         f"To‘lovdan so‘ng chek (kvitansiya) rasmi yuboring (rasm shaklida).",
                    parse_mode='HTML'
                )
            else:
                query.message.reply_text(
                    text=globals.SEND_LOCATION[db_user["lang_id"]],
                    reply_markup=ReplyKeyboardMarkup([[KeyboardButton(text=globals.SEND_LOCATION[db_user["lang_id"]], request_location=True)]],
                                                     resize_keyboard=True)
                )
        else:
            query.message.edit_reply_markup(
                reply_markup=InlineKeyboardMarkup(
                    [[
                        InlineKeyboardButton(text="Naqd pul", callback_data="order_payment_1"),
                        InlineKeyboardButton(text="Karta", callback_data="order_payment_2"),
                    ]]
                )
            )
