import os
import shutil
import asyncio
import json
import base64
import requests
import time
import uuid
import random
from concurrent.futures import ThreadPoolExecutor, as_completed
from aiogram import Bot, Dispatcher, F, Router
from aiogram.types import Message, FSInputFile
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

# ==========================================
# تنظیمات اصلی
# ==========================================
# 💡 توکن اکنون به صورت امن از متغیرهای محیطی Railway خوانده می‌شود
BOT_TOKEN = os.getenv("BOT_TOKEN")

router = Router()

SESSION_BASE_DIR = "basket_sessions"
if os.path.exists(SESSION_BASE_DIR):
    shutil.rmtree(SESSION_BASE_DIR, ignore_errors=True)
os.makedirs(SESSION_BASE_DIR, exist_ok=True)

# تعریف استیت برای دریافت شماره الگو
class CopierState(StatesGroup):
    waiting_for_template = State()

# ==========================================
# لیست پروکسی‌ها
# ==========================================
PROXY_LIST = [
    "http://n4w32tknlcwt:cr4ownjm7lrjb1a@216.26.233.27:3129",
    "http://n4w32tknlcwt:cr4ownjm7lrjb1a@45.3.46.118:3129",
    "http://n4w32tknlcwt:cr4ownjm7lrjb1a@65.111.25.207:3129",
    "http://n4w32tknlcwt:cr4ownjm7lrjb1a@216.26.252.246:3129",
    "http://n4w32tknlcwt:cr4ownjm7lrjb1a@216.26.228.132:3129",
    "http://n4w32tknlcwt:cr4ownjm7lrjb1a@65.111.7.216:3129",
    "http://n4w32tknlcwt:cr4ownjm7lrjb1a@45.3.37.252:3129",
    "http://n4w32tknlcwt:cr4ownjm7lrjb1a@65.111.8.18:3129",
    "http://n4w32tknlcwt:cr4ownjm7lrjb1a@104.207.60.245:3129",
    "http://n4w32tknlcwt:cr4ownjm7lrjb1a@216.26.253.183:3129",
    "http://n4w32tknlcwt:cr4ownjm7lrjb1a@65.111.22.183:3129",
    "http://n4w32tknlcwt:cr4ownjm7lrjb1a@104.207.61.86:3129",
    "http://n4w32tknlcwt:cr4ownjm7lrjb1a@104.207.58.25:3129",
    "http://n4w32tknlcwt:cr4ownjm7lrjb1a@65.111.29.220:3129",
    "http://n4w32tknlcwt:cr4ownjm7lrjb1a@104.207.36.130:3129",
    "http://n4w32tknlcwt:cr4ownjm7lrjb1a@104.167.19.186:3129",
    "http://n4w32tknlcwt:cr4ownjm7lrjb1a@65.111.0.21:3129",
    "http://n4w32tknlcwt:cr4ownjm7lrjb1a@104.207.42.226:3129",
    "http://n4w32tknlcwt:cr4ownjm7lrjb1a@104.207.38.77:3129",
    "http://n4w32tknlcwt:cr4ownjm7lrjb1a@209.50.188.206:3129",
    "http://n4w32tknlcwt:cr4ownjm7lrjb1a@216.26.226.201:3129",
    "http://n4w32tknlcwt:cr4ownjm7lrjb1a@209.50.180.25:3129",
    "http://n4w32tknlcwt:cr4ownjm7lrjb1a@209.50.173.190:3129",
    "http://n4w32tknlcwt:cr4ownjm7lrjb1a@65.111.14.98:3129",
    "http://n4w32tknlcwt:cr4ownjm7lrjb1a@45.3.43.79:3129",
    "http://n4w32tknlcwt:cr4ownjm7lrjb1a@104.207.33.25:3129",
    "http://n4w32tknlcwt:cr4ownjm7lrjb1a@151.123.177.253:3129",
    "http://n4w32tknlcwt:cr4ownjm7lrjb1a@216.26.245.67:3129",
    "http://n4w32tknlcwt:cr4ownjm7lrjb1a@216.26.247.93:3129",
    "http://n4w32tknlcwt:cr4ownjm7lrjb1a@45.3.35.181:3129",
    "http://n4w32tknlcwt:cr4ownjm7lrjb1a@45.3.34.7:3129"
]

def get_random_proxy():
    selected = random.choice(PROXY_LIST)
    return {"http": selected, "https": selected}

# ==========================================
# توابع کار با فایل و توکن
# ==========================================
def get_tokens_from_file(file_path):
    access_token, refresh_token = None, None
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            for cookie in data.get('cookies', []):
                if cookie.get('name') == 'tokenMS':
                    access_token = cookie.get('value')
                elif cookie.get('name') == 'refresh_token':
                    refresh_token = cookie.get('value')
            if not access_token or not refresh_token:
                for origin in data.get('origins', []):
                    for item in origin.get('localStorage', []):
                        if item.get('name') == 'tokenMS':
                            access_token = item.get('value')
                        elif item.get('name') == 'refresh_token':
                            refresh_token = item.get('value')
    except Exception:
        pass
    return access_token, refresh_token

def update_file_with_new_tokens(file_path, old_acc, new_acc, old_ref, new_ref):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        if old_acc and new_acc:
            content = content.replace(old_acc, new_acc)
        if old_ref and new_ref:
            content = content.replace(old_ref, new_ref)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
    except Exception:
        pass

def get_user_id_from_token(token):
    try:
        payload = token.split('.')[1]
        payload += '=' * (-len(payload) % 4)
        decoded_bytes = base64.urlsafe_b64decode(payload)
        data = json.loads(decoded_bytes)
        
        uid = data.get('userId') or data.get('alternativeCustomerId')
        if uid:
            return int(uid) 
        return 0
    except Exception:
        return 0

# ==========================================
# کلاس API
# ==========================================
class OkalaAPI:
    def __init__(self):
        self.base_headers = {
            'accept': 'application/json, text/plain, */*',
            'source': 'okala',
            'ui-version': '2.0',
            'origin': 'https://www.okala.com',
            'sec-ch-ua': '"Chromium";v="137", "Not/A)Brand";v="24"',
            'sec-ch-ua-mobile': '?1',
            'sec-ch-ua-platform': '"Android"',
            'User-Agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 Chrome/137.0.0.0 Mobile'
        }

    def make_request(self, method, url, access_token=None, **kwargs):
        headers = self.base_headers.copy()
        headers['X-Correlation-Id'] = str(uuid.uuid4())
        headers['X-User-Unique-Id'] = str(uuid.uuid4())
        headers['session-id'] = str(uuid.uuid4())

        if access_token:
            headers['Authorization'] = f'Bearer {access_token}'

        if 'headers' in kwargs:
            headers.update(kwargs.pop('headers'))

        for attempt in range(3):
            current_proxy = get_random_proxy()
            try:
                res = requests.request(method, url, headers=headers, proxies=current_proxy, timeout=45, **kwargs)
                if res.status_code == 200:
                    try:
                        return 200, res.json()
                    except:
                        return 200, {}
                elif res.status_code == 401:
                    return 401, {}
                else:
                    return res.status_code, res.text 
            except Exception:
                time.sleep(1.5)
                continue
                
        return 0, "Network Error"

    def refresh_token(self, refresh_token):
        url = "https://apigateway.okala.com/api/v1/accounts/tokens"
        data = {
            "grant_type": "refresh_token",
            "client_id": "customer_client_id",
            "client_secret": "u_M{'57j!%LI21#",
            "scope": "offline_access",
            "refresh_token": refresh_token
        }
        headers = {"content-type": "application/x-www-form-urlencoded"}
        status, response_data = self.make_request('POST', url, headers=headers, data=data)
        if status == 200 and isinstance(response_data, dict):
            return response_data.get('access_token'), response_data.get('refresh_token')
        return None, None

    def get_address(self, token, uid):
        url = 'https://apigateway.okala.com/api/voyager/CustomerAddress/CustomerAddressForReact'
        return self.make_request('GET', url, token, params={'customerId': uid})

    def add_address(self, token, uid, addr_data):
        url = 'https://apigateway.okala.com/api/voyager/C/CustomerAccount/AddAddress/'
        
        plaque_val = addr_data.get('plaque')
        if not plaque_val or plaque_val == "None": plaque_val = '0'
        
        unit_val = addr_data.get('unit')
        if not unit_val or unit_val == "None": unit_val = '1'

        address_text = addr_data.get('address')
        if not address_text or str(address_text).strip() == "":
            address_text = "آدرس ثبت شده"

        payload = {
            'id': 0, 
            'customerId': uid, 
            'mobilePhone': '', 
            'ShoppingSectorPartId': '0',
            'shoppingSectorId': '0', 
            'plaque': str(plaque_val), 
            'unit': str(unit_val), 
            'lat': float(addr_data['lat']),
            'lng': float(addr_data['lng']), 
            'title': None, 
            'addressTypeId': 3, 
            'oprationDuration': random.randint(10000, 20000), 
            'address': address_text,
            'mapPlatform': 'ParsiMap'
        }
        return self.make_request('POST', url, token, json=payload)

    def get_stores(self, token, lat, lng, uid):
        url = 'https://apigateway.okala.com/api/Lucifer/v1/StoreRanking/GetAllStores'
        params = {'latitude': lat, 'longitude': lng, 'CustomerId': uid, 'IsMsBasketEnable': 'true'}
        return self.make_request('GET', url, token, params=params)

    def get_cart(self, token, uid, store_ids):
        url = 'https://apigateway.okala.com/api/Basket/v2/ShoppingCart/GetCustomerShoppingCartItems'
        params = {'CustomerId': uid, 'StoreIds': store_ids, 'isFromCartPage': 'false'}
        return self.make_request('GET', url, token, params=params)

    def add_to_cart(self, token, uid, store_id, product_id):
        url = 'https://apigateway.okala.com/api/Basket/v2/ShoppingCart/AddToShoppingCart'
        payload = {
            'storeId': store_id, 'customerId': uid, 'productId': product_id, 'quantity': 1,
            'isSupplier': False, 'replaceItemMethodCode': -1, 'sectorId': '0', 'sectorPartId': '0',
            'productStoreId': '0', 'queryId': None
        }
        return self.make_request('POST', url, token, json=payload)

# ==========================================
# Worker: پردازش اکانت‌های هدف
# ==========================================
def worker_copy_basket(file_path, filename, api, template_data):
    time.sleep(random.uniform(0.1, 1.0))
    
    acc_token, ref_token = get_tokens_from_file(file_path)
    if not acc_token:
        return filename, "error_token"

    uid = get_user_id_from_token(acc_token)
    if not uid or uid == 0:
        return filename, "error_uuid"

    status, response_data = api.add_address(acc_token, uid, template_data['address'])
    
    if status == 401 and ref_token:
        new_acc, new_ref = api.refresh_token(ref_token)
        if new_acc:
            update_file_with_new_tokens(file_path, acc_token, new_acc, ref_token, new_ref)
            acc_token = new_acc
            status, response_data = api.add_address(acc_token, uid, template_data['address'])

    if status != 200:
        return filename, "error_address"

    added_count = 0
    for item in template_data['items']:
        for _ in range(item['quantity']):
            c_status, _ = api.add_to_cart(acc_token, uid, template_data['store_id'], item['productId'])
            if c_status == 200:
                added_count += 1
            time.sleep(random.uniform(0.3, 0.8))

    if added_count == 0 and len(template_data['items']) > 0:
        return filename, "error_cart"

    return filename, "success"

# ==========================================
# هسته اصلی: پردازش الگو
# ==========================================
def process_all_baskets(extracted_dir, session_dir, template_query):
    src_accounts = None
    for root, dirs, files in os.walk(extracted_dir):
        if 'accounts' in dirs and not src_accounts:
            src_accounts = os.path.join(root, 'accounts')
            break

    if not src_accounts:
        return None, "❌ پوشه 'accounts' داخل فایل زیپ پیدا نشد."

    all_files = sorted([f for f in os.listdir(src_accounts) if os.path.isfile(os.path.join(src_accounts, f))])
    
    if len(all_files) < 2:
        return None, "❌ فایل زیپ باید حداقل شامل ۲ اکانت باشد (۱ الگو + حداقل ۱ هدف)."

    template_file = None
    for f in all_files:
        if template_query in f:
            template_file = f
            break

    if not template_file:
        return None, f"❌ هیچ اکانتی که شامل عبارت '{template_query}' در نام خود باشد، در فایل زیپ یافت نشد!"

    target_files = [f for f in all_files if f != template_file]
    
    print(f"\n🚀 شروع عملیات. فایل الگو: {template_file}")
    api = OkalaAPI()

    t_path = os.path.join(src_accounts, template_file)
    t_acc, t_ref = get_tokens_from_file(t_path)
    t_uid = get_user_id_from_token(t_acc)

    if not t_uid or t_uid == 0:
        return None, "❌ ساختار توکن اکانت الگو خراب است."

    status, addr_res = api.get_address(t_acc, t_uid)
    if status == 401 and t_ref:
        t_acc, t_ref = api.refresh_token(t_ref)
        if t_acc:
            update_file_with_new_tokens(t_path, t_acc, t_acc, t_ref, t_ref)
            status, addr_res = api.get_address(t_acc, t_uid)

    if status != 200 or not isinstance(addr_res, dict) or not addr_res.get('data'):
        return None, f"❌ اکانت الگو فاقد آدرس است. پاسخ سرور: {addr_res}"

    template_addr = addr_res['data'][0]

    status, stores_res = api.get_stores(t_acc, template_addr['lat'], template_addr['lng'], t_uid)
    if status != 200 or not isinstance(stores_res, dict) or not stores_res.get('data', {}).get('stores'):
        return None, f"❌ هیچ فروشگاهی برای آدرس اکانت الگو یافت نشد."

    store_ids = [s['storeId'] for s in stores_res['data']['stores']]

    status, cart_res = api.get_cart(t_acc, t_uid, store_ids)
    if status != 200 or not isinstance(cart_res, dict) or not cart_res.get('data', {}).get('result'):
        return None, f"❌ امکان دریافت سبد خرید اکانت الگو وجود ندارد."

    cart_data = cart_res['data']['result'][0]
    cart_items = cart_data.get('items', [])
    cart_store_id = cart_data.get('storeId')

    if not cart_items:
        return None, f"❌ سبد خرید اکانت الگو ({template_file}) خالی است!"

    addr_text = template_addr.get('address')
    if not addr_text: addr_text = "آدرس ثبت شده"

    template_data = {
        'address': {
            'lat': template_addr['lat'],
            'lng': template_addr['lng'],
            'address': addr_text,
            'plaque': template_addr.get('plaque', '0'),
            'unit': template_addr.get('unit', '1')
        },
        'store_id': cart_store_id,
        'items': cart_items
    }

    print(f"✅ اطلاعات الگو با موفقیت دریافت شد. در حال کپی روی {len(target_files)} اکانت...")

    stats = {"total_targets": len(target_files), "success": 0, "error_address": 0, "error_cart": 0, "error_token": 0}
    
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {
            executor.submit(worker_copy_basket, os.path.join(src_accounts, filename), filename, api, template_data): filename 
            for filename in target_files
        }
        
        for future in as_completed(futures):
            filename, result = future.result()
            if result == "success":
                stats["success"] += 1
                print(f"   ✅ [موفق] {filename} -> کپی سبد انجام شد.")
            elif result in ["error_token", "error_uuid"]:
                stats["error_token"] += 1
            elif result == "error_address":
                stats["error_address"] += 1
            elif result == "error_cart":
                stats["error_cart"] += 1
                print(f"   ❌ [خطا] {filename} -> افزودن کالا ناموفق.")

    final_zip_base = os.path.join(session_dir, "Updated_Accounts")
    final_zip_path = shutil.make_archive(final_zip_base, 'zip', extracted_dir)

    return (final_zip_path, template_file, template_data, stats), None

# ==========================================
# هندلرهای تلگرام
# ==========================================
@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "سلام عرفان! 👋\n\n"
        "به ربات **کپی‌کننده سبد خرید (نسخه Railway)** خوش آمدی 🛒\n\n"
        "کافیست فایل زیپ اکانت‌ها را بفرستی."
    )

@router.message(F.document)
async def handle_zip_document(message: Message, bot: Bot, state: FSMContext):
    if not message.document.file_name.lower().endswith('.zip'):
        await message.answer("❌ لطفاً فقط فایل زیپ (.zip) ارسال کن.")
        return

    msg = await message.answer("⏳ در حال دانلود و استخراج فایل...")

    session_id = str(uuid.uuid4())
    session_dir = os.path.join(SESSION_BASE_DIR, session_id)
    os.makedirs(session_dir, exist_ok=True)
    
    extracted_dir = os.path.join(session_dir, "extracted")
    zip_path = os.path.join(session_dir, "uploaded.zip")
    
    file_info = await bot.get_file(message.document.file_id)
    await bot.download_file(file_info.file_path, zip_path)
    
    try:
        shutil.unpack_archive(zip_path, extracted_dir)
    except Exception:
        await msg.edit_text("❌ فایل زیپ مشکل دارد و استخراج نشد.")
        shutil.rmtree(session_dir, ignore_errors=True)
        return

    await state.update_data(session_dir=session_dir, extracted_dir=extracted_dir)
    await state.set_state(CopierState.waiting_for_template)

    await msg.edit_text(
        "✅ فایل زیپ با موفقیت دریافت و استخراج شد.\n\n"
        "👇 لطفاً **شماره موبایل اکانت الگو** (یا بخشی از نام فایل آن) را در چت بفرست تا ربات آن را پیدا کند و عملیات آغاز شود:"
    )

@router.message(CopierState.waiting_for_template, F.text)
async def handle_template_number(message: Message, state: FSMContext, bot: Bot):
    template_query = message.text.strip()
    
    data = await state.get_data()
    session_dir = data.get('session_dir')
    extracted_dir = data.get('extracted_dir')

    await state.clear()

    msg = await message.answer(f"🔍 در حال جستجوی اکانت حاوی ` {template_query} ` و اجرای عملیات کپی...")
    
    result_data, error_msg = await asyncio.to_thread(process_all_baskets, extracted_dir, session_dir, template_query)

    if error_msg:
        await msg.edit_text(error_msg)
        shutil.rmtree(session_dir, ignore_errors=True)
        return

    final_zip_path, template_file, template_data, stats = result_data
    await msg.delete()

    total_qty = sum(item['quantity'] for item in template_data['items'])

    report_text = (
        "📊 <b>گزارش نهایی کپی سبد خرید:</b>\n\n"
        f"👑 <b>اکانت الگو:</b> {template_file}\n"
        f"🛒 <b>سبد الگو:</b> {len(template_data['items'])} مدل کالا (تعداد کل: {total_qty} عدد)\n\n"
        f"🎯 کل اکانت‌های هدف: <b>{stats['total_targets']}</b>\n"
        f"✅ کپی موفق: <b>{stats['success']}</b> اکانت\n"
        f"❌ خطای ثبت آدرس: <b>{stats['error_address']}</b> اکانت\n"
        f"❌ خطای افزودن کالا: <b>{stats['error_cart']}</b> اکانت\n"
        f"🔒 منقضی/بدون توکن: <b>{stats['error_token']}</b> اکانت\n\n"
        "👇 <b>فایل نهایی ضمیمه شد:</b>"
    )

    await message.answer_document(document=FSInputFile(final_zip_path), caption=report_text, parse_mode="HTML")
    shutil.rmtree(session_dir, ignore_errors=True)

async def main():
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()
    dp.include_router(router)
    print("🤖 Basket Copier Bot (Railway Ready) is running...")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
