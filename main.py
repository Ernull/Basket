import os
import shutil
import asyncio
import json
import base64
import requests
import time
import uuid
import random
import re
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from aiogram import Bot, Dispatcher, F, Router
from aiogram.types import Message, FSInputFile
from aiogram.filters import Command

BOT_TOKEN = os.getenv("BOT_TOKEN")

router = Router()

SESSION_BASE_DIR = "basket_sessions"
if os.path.exists(SESSION_BASE_DIR):
    shutil.rmtree(SESSION_BASE_DIR, ignore_errors=True)
os.makedirs(SESSION_BASE_DIR, exist_ok=True)

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

def fetch_data(url):
    try:
        res = requests.get(url, timeout=15)
        if res.status_code == 200:
            return res.json()
    except Exception:
        pass
    return None

def get_tokens_from_data(data):
    access_token, refresh_token = None, None
    try:
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

def update_tokens_in_data(data, old_acc, new_acc, old_ref, new_ref):
    try:
        content = json.dumps(data, ensure_ascii=False)
        if old_acc and new_acc:
            content = content.replace(old_acc, new_acc)
        if old_ref and new_ref:
            content = content.replace(old_ref, new_ref)
        return json.loads(content)
    except Exception:
        return data

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

class OkalaAPI:
    def __init__(self):
        self.request_logs = []  # ذخیره لیست تمام لاگ‌ها
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

    def log_request(self, method, url, status_code, response_text):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] {method} {url}\nStatus: {status_code}\nResponse: {response_text}\n{'-'*50}\n"
        self.request_logs.append(log_entry)

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
                self.log_request(method, url, res.status_code, res.text)
                
                if res.status_code == 200:
                    try:
                        return 200, res.json()
                    except:
                        return 200, {}
                elif res.status_code == 401:
                    return 401, {}
                else:
                    return res.status_code, res.text 
            except Exception as e:
                self.log_request(method, url, "EXCEPTION", str(e))
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
        
        plaque_val = addr_data.get('plaque', '0')
        unit_val = addr_data.get('unit', '1')
        address_text = addr_data.get('address', 'آدرس ثبت شده از نقشه')

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


def worker_copy_basket(target_url, api, template_data):
    time.sleep(random.uniform(0.1, 1.0))
    
    data = fetch_data(target_url)
    if not data:
        return target_url, "error_fetch", None
    
    acc_token, ref_token = get_tokens_from_data(data)
    if not acc_token:
        return target_url, "error_token", data

    uid = get_user_id_from_token(acc_token)
    if not uid or uid == 0:
        return target_url, "error_uuid", data

    status, response_data = api.add_address(acc_token, uid, template_data['address'])
    
    if status == 401 and ref_token:
        new_acc, new_ref = api.refresh_token(ref_token)
        if new_acc:
            data = update_tokens_in_data(data, acc_token, new_acc, ref_token, new_ref)
            acc_token = new_acc
            status, response_data = api.add_address(acc_token, uid, template_data['address'])

    if status != 200:
        return target_url, "error_address", data

    added_count = 0
    for item in template_data['items']:
        for _ in range(item['quantity']):
            c_status, _ = api.add_to_cart(acc_token, uid, template_data['store_id'], item['productId'])
            if c_status == 200:
                added_count += 1
            time.sleep(random.uniform(0.3, 0.8))

    if added_count == 0 and len(template_data['items']) > 0:
        return target_url, "error_cart", data

    return target_url, "success", data


def process_all_links(session_dir, template_url, target_urls):
    api = OkalaAPI()

    template_data_json = fetch_data(template_url)
    if not template_data_json:
        return None, None, "خطا: امکان دریافت اطلاعات اکانت مرجع (اولین لینک) وجود ندارد."

    t_acc, t_ref = get_tokens_from_data(template_data_json)
    t_uid = get_user_id_from_token(t_acc)

    if not t_uid or t_uid == 0:
        return None, None, "خطا: ساختار توکن اکانت مرجع معتبر نمی‌باشد."

    status, addr_res = api.get_address(t_acc, t_uid)
    if status == 401 and t_ref:
        t_acc, t_ref = api.refresh_token(t_ref)
        if t_acc:
            template_data_json = update_tokens_in_data(template_data_json, t_acc, t_acc, t_ref, t_ref)
            status, addr_res = api.get_address(t_acc, t_uid)

    template_addr = None
    if status == 200 and isinstance(addr_res, dict) and addr_res.get('data'):
        # آدرس از API با موفقیت دریافت شد
        template_addr = addr_res['data'][0]
    else:
        # مکانیزم هوشمند جایگزین (Fallback) در صورتی که کاربر هیچ آدرسی ثبت نکرده باشد
        api.request_logs.append(f"INFO: No saved address found for template account. Using mapInfo as fallback.\n{'-'*50}\n")
        lat, lng = 35.69975, 51.33551 # مختصات پیش‌فرض (تهران) در صورت خطا
        addr_text = "آدرس استخراج شده از نقشه"
        try:
            for origin in template_data_json.get('origins', []):
                for item in origin.get('localStorage', []):
                    if item.get('name') == 'mapInfo':
                        map_info = json.loads(item.get('value'))
                        if 'selectedCity' in map_info:
                            lat = map_info['selectedCity']['lat']
                            lng = map_info['selectedCity']['lng']
                            addr_text = map_info['selectedCity'].get('name', addr_text)
        except Exception as e:
            api.request_logs.append(f"ERROR parsing mapInfo: {e}\n{'-'*50}\n")
            
        template_addr = {
            'lat': lat,
            'lng': lng,
            'address': addr_text,
            'plaque': '0',
            'unit': '1'
        }

    status, stores_res = api.get_stores(t_acc, template_addr['lat'], template_addr['lng'], t_uid)
    if status != 200 or not isinstance(stores_res, dict) or not stores_res.get('data', {}).get('stores'):
        return None, api.request_logs, "خطا: هیچ فروشگاهی برای مختصات اکانت مرجع یافت نشد."

    store_ids = [s['storeId'] for s in stores_res['data']['stores']]

    status, cart_res = api.get_cart(t_acc, t_uid, store_ids)
    if status != 200 or not isinstance(cart_res, dict) or not cart_res.get('data', {}).get('result'):
        return None, api.request_logs, "خطا: امکان بازیابی سبد خرید اکانت مرجع وجود ندارد."

    cart_data = cart_res['data']['result'][0]
    cart_items = cart_data.get('items', [])
    cart_store_id = cart_data.get('storeId')

    if not cart_items:
        return None, api.request_logs, "خطا: سبد خرید اکانت مرجع خالی است."

    template_data = {
        'address': {
            'lat': template_addr['lat'],
            'lng': template_addr['lng'],
            'address': template_addr.get('address', 'آدرس ثبت شده'),
            'plaque': template_addr.get('plaque', '0'),
            'unit': template_addr.get('unit', '1')
        },
        'store_id': cart_store_id,
        'items': cart_items
    }

    stats = {
        "total_targets": len(target_urls), 
        "success": 0, 
        "error_fetch": 0, 
        "error_address": 0, 
        "error_cart": 0, 
        "error_token": 0
    }
    
    updated_dir = os.path.join(session_dir, "Updated_Accounts")
    os.makedirs(updated_dir, exist_ok=True)

    with open(os.path.join(updated_dir, "template_account.json"), "w", encoding="utf-8") as f:
        json.dump(template_data_json, f, ensure_ascii=False, indent=2)

    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {
            executor.submit(worker_copy_basket, url, api, template_data): url 
            for url in target_urls
        }
        
        counter = 1
        for future in as_completed(futures):
            url = futures[future]
            try:
                _, result, updated_json = future.result()
                if result == "success":
                    stats["success"] += 1
                elif result == "error_fetch":
                    stats["error_fetch"] += 1
                elif result in ["error_token", "error_uuid"]:
                    stats["error_token"] += 1
                elif result == "error_address":
                    stats["error_address"] += 1
                elif result == "error_cart":
                    stats["error_cart"] += 1
                
                if updated_json:
                    file_name = url.strip('/').split('/')[-1]
                    if not file_name or len(file_name) < 5:
                        file_name = f"target_account_{counter}"
                    with open(os.path.join(updated_dir, f"{file_name}.json"), "w", encoding="utf-8") as f:
                        json.dump(updated_json, f, ensure_ascii=False, indent=2)
                counter += 1
            except Exception:
                stats["error_fetch"] += 1

    final_zip_base = os.path.join(session_dir, "Updated_Accounts_Data")
    final_zip_path = shutil.make_archive(final_zip_base, 'zip', updated_dir)

    return (final_zip_path, template_data, stats), api.request_logs, None


@router.message(Command("start"))
async def cmd_start(message: Message):
    await message.answer(
        "سیستم همگام‌سازی سبد خرید فعال است.\n\n"
        "لطفاً لیست لینک‌های خود را در یک پیام بفرستید.\n\n"
        "🟢 توجه: **اولین لینک** ارسالی در پیام، به عنوان اکانت **مرجع (الگو)** شناخته خواهد شد."
    )

@router.message(F.text)
async def handle_links_message(message: Message):
    urls = re.findall(r'(https?://\S+)', message.text)
    
    if len(urls) < 2:
        await message.answer("خطا: لطفاً حداقل ۲ لینک (یک الگو و حداقل یک هدف) ارسال کنید.")
        return

    template_url = urls[0]
    target_urls = urls[1:]

    msg = await message.answer(f"در حال پردازش...\nاکانت مرجع دریافت شد. تعداد اهداف: {len(target_urls)}")

    session_id = str(uuid.uuid4())
    session_dir = os.path.join(SESSION_BASE_DIR, session_id)
    os.makedirs(session_dir, exist_ok=True)
    
    result_data, logs, error_msg = await asyncio.to_thread(process_all_links, session_dir, template_url, target_urls)

    # ایجاد فایل گزارش دیباگ در هر شرایطی (حتی اگر خطا رخ داده باشد)
    log_file_path = os.path.join(session_dir, "debug_report.txt")
    if logs:
        with open(log_file_path, "w", encoding="utf-8") as f:
            f.write("\n".join(logs))

    if error_msg:
        await msg.edit_text(error_msg)
        if os.path.exists(log_file_path):
            await message.answer_document(document=FSInputFile(log_file_path), caption="فایل گزارش خطاها (Debug Log)")
        shutil.rmtree(session_dir, ignore_errors=True)
        return

    final_zip_path, template_data, stats = result_data
    await msg.delete()

    total_qty = sum(item['quantity'] for item in template_data['items'])

    report_text = (
        "✅ گزارش عملکرد همگام‌سازی:\n\n"
        f"تعداد اقلام مرجع: {len(template_data['items'])} مدل (مجموع: {total_qty} عدد)\n\n"
        f"تعداد کل اهداف: {stats['total_targets']}\n"
        f"🟢 موفق: {stats['success']}\n"
        f"🔴 خطای دریافت از لینک: {stats['error_fetch']}\n"
        f"🔴 خطای ثبت آدرس: {stats['error_address']}\n"
        f"🔴 خطای افزودن کالا: {stats['error_cart']}\n"
        f"🔴 خطای احراز هویت / توکن: {stats['error_token']}\n\n"
        "فایل ZIP اکانت‌ها و فایل Debug پیوست شدند."
    )

    await message.answer_document(document=FSInputFile(final_zip_path), caption=report_text)
    if os.path.exists(log_file_path):
        await message.answer_document(document=FSInputFile(log_file_path), caption="گزارش کامل درخواست‌ها و پاسخ‌های سرور (Debug Log)")
    
    shutil.rmtree(session_dir, ignore_errors=True)

async def main():
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()
    dp.include_router(router)
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
