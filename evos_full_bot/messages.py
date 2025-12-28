import os
import time
import methods
from register import check, check_data_decorator
from database import Database
import globals
from telegram import KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import ConversationHandler

ADMIN_ID = 1482897133

IMAGE_DIR = os.path.join(os.path.dirname(__file__), 'images')
if not os.path.exists(IMAGE_DIR):
    os.makedirs(IMAGE_DIR, exist_ok=True)

db = Database("db-evos.db")


@check_data_decorator
def message_handler(update, context):
    message = update.message.text
    user = update.message.from_user
    state = context.user_data.get("state", 0)
    db_user = db.get_user_by_chat_id(user.id)
    if state == 0:
        check(update, context)

    elif state == 1:
        # original registration flows unchanged...
        check(update, context)

    ################## lesson-4 ###################
    elif state == 2:
        # original order/menu handling unchanged (kept as pass here for brevity)
        pass

    else:
        update.message.reply_text("Salom")


# Admin: start adding product
def admin_add_product_start(update, context):
    user = update.effective_user
    if user.id != ADMIN_ID:
        return
    context.user_data['admin_action'] = 'add_product'
    context.user_data['admin_step'] = 'category'
    # show categories
    cats = db.get_categories_by_parent()
    text = "Kategoriyalar:\n"
    for c in cats:
        text += f"{c['id']} - {c.get('name_uz') or c.get('name_ru')}\n"
    text += "\nIltimos, mahsulot qo'shish uchun category id kiriting (son):"
    update.message.reply_text(text)


def admin_flow_handler(update, context):
    user = update.effective_user
    if user.id != ADMIN_ID:
        return
    action = context.user_data.get('admin_action')
    if not action:
        return
    step = context.user_data.get('admin_step')
    text = update.message.text

    if action == 'add_product':
        if step == 'category':
            try:
                category_id = int(text.strip())
            except:
                update.message.reply_text('Iltimos kategoriyaning raqamini yuboring (son).')
                return
            context.user_data['new_product'] = {'category_id': category_id}
            context.user_data['admin_step'] = 'name_uz'
            update.message.reply_text('Mahsulot nomi (O\'zbekcha) yuboring:')

        elif step == 'name_uz':
            context.user_data['new_product']['name_uz'] = text
            context.user_data['admin_step'] = 'name_ru'
            update.message.reply_text('Mahsulot nomi (Ruscha) yuboring:')

        elif step == 'name_ru':
            context.user_data['new_product']['name_ru'] = text
            context.user_data['admin_step'] = 'desc_uz'
            update.message.reply_text('Mahsulot ta\'rifi (O\'zbekcha) yuboring:')

        elif step == 'desc_uz':
            context.user_data['new_product']['description_uz'] = text
            context.user_data['admin_step'] = 'desc_ru'
            update.message.reply_text('Mahsulot ta\'rifi (Ruscha) yuboring:')

        elif step == 'desc_ru':
            context.user_data['new_product']['description_ru'] = text
            context.user_data['admin_step'] = 'price'
            update.message.reply_text('Mahsulot narxini son bilan yuboring (misol: 2000):')

        elif step == 'price':
            try:
                price = int(text.strip())
            except:
                update.message.reply_text('Narxni son bilan yuboring (misol: 2000)')
                return
            context.user_data['new_product']['price'] = price
            context.user_data['admin_step'] = 'image'
            update.message.reply_text('Iltimos mahsulot rasmini yuboring (photo).')


# photo handler: foydalanuvchi chek (kvitan­siya) rasmi yuborganida ishlaydi
def photo_handler(update, context):
    user = update.message.from_user
    db_user = db.get_user_by_chat_id(user.id)
    # Admin adding product image
    if user.id == ADMIN_ID and context.user_data.get('admin_action') == 'add_product' and context.user_data.get('admin_step') == 'image':
        photo = update.message.photo[-1]
        file = context.bot.get_file(photo.file_id)
        filename = f"prod_{int(time.time())}_{photo.file_id}.jpg"
        path = os.path.join(IMAGE_DIR, filename)
        file.download(path)
        newp = context.user_data.get('new_product', {})
        db.add_product(
            category_id=newp.get('category_id'),
            name_uz=newp.get('name_uz'),
            name_ru=newp.get('name_ru'),
            description_uz=newp.get('description_uz'),
            description_ru=newp.get('description_ru'),
            price=newp.get('price'),
            image_path=path
        )
        update.message.reply_text('Mahsulot qo\'shildi va ma\'lumotlar saqlandi.')
        context.user_data.pop('admin_action', None)
        context.user_data.pop('admin_step', None)
        context.user_data.pop('new_product', None)
        return

    # Agar foydalanuvchi chek yuborishi kutilayotgan bo'lsa
    if context.user_data.get('expecting_receipt'):
        photo = update.message.photo[-1]  # eng yuqori sifatli file
        file_id = photo.file_id
        context.user_data['receipt_file_id'] = file_id
        context.user_data['expecting_receipt'] = False
        update.message.reply_text(
            text="Rasim qabul qilindi. Iltimos, endi yetkazib berish manzilini (joylashuvni) yuboring.",
        )
    else:
        update.message.reply_text("Rasm qabul qilindi, ammo hech qanday buyurtma uchun chek yuborilayotgani aniqlanmadi. Agar buyurtma bermoqchi bo'lsangiz, menyudan boshlang.")


# Admin: delete product with /del_product <id>
def admin_delete_product(update, context):
    user = update.effective_user
    if user.id != ADMIN_ID:
        return
    args = context.args
    if not args:
        update.message.reply_text('Iltimos /del_product <product_id> shaklida yuboring.')
        return
    try:
        pid = int(args[0])
    except:
        update.message.reply_text('Product id son bo\'lishi kerak.')
        return
    db.delete_product(pid)
    update.message.reply_text(f'Product {pid} o\'chirildi (agar mavjud bo\'lsa).')


# Admin: accept/reject orders
def admin_accept_order(update, context):
    user = update.effective_user
    if user.id != ADMIN_ID:
        return
    args = context.args
    if not args:
        update.message.reply_text('Iltimos /accept_order <order_id> shaklida yuboring.')
        return
    try:
        oid = int(args[0])
    except:
        update.message.reply_text('Order id son bo\'lishi kerak.')
        return
    db.update_order_status(oid, 2)  # 2 = accepted
    update.message.reply_text(f'Buyurtma {oid} qabul qilindi.')


def admin_reject_order(update, context):
    user = update.effective_user
    if user.id != ADMIN_ID:
        return
    args = context.args
    if not args:
        update.message.reply_text('Iltimos /reject_order <order_id> shaklida yuboring.')
        return
    try:
        oid = int(args[0])
    except:
        update.message.reply_text('Order id son bo\'lishi kerak.')
        return
    db.update_order_status(oid, 3)  # 3 = rejected
    update.message.reply_text(f'Buyurtma {oid} rad etildi.')
