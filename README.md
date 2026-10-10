# Bitpin AI Connector

[![Tests](https://github.com/Erfouni/bitpin-ai-connector/actions/workflows/tests.yml/badge.svg)](https://github.com/Erfouni/bitpin-ai-connector/actions/workflows/tests.yml)

**فارسی** · [English](README.en.md)

<div dir="rtl">

اتصال مستقیم **بیت‌پین به ChatGPT، Claude و کلاینت‌های MCP** برای مشاهدهٔ دارایی، تحلیل بازار، ثبت خرید و فروش و مدیریت سفارش‌ها.

این پروژه مستقل از AI Trader است: تصمیم از گفت‌وگوی شما با مدل می‌آید و این سرور ابزار اتصال را فراهم می‌کند. استراتژی، زمان‌بند معامله یا وابستگی به ربات ندارد. برای نصب، **کلید OpenAI یا Anthropic لازم نیست**.

## کوتاه‌ترین مسیر نصب

اگر روی سرور لینوکس `git` و `curl` دارید، دامنه به آن وصل است و پورت‌های 80 و 443 آزادند، در پوشه‌ای که قبلاً پروژه را دریافت نکرده‌اید همین یک دستور را اجرا کنید:

</div>

```bash
git clone https://github.com/Erfouni/bitpin-ai-connector.git && cd bitpin-ai-connector && bash install.sh
```

<div dir="rtl">

نصب‌کننده نصب Docker را پیشنهاد می‌کند، IP خروجی را نشان می‌دهد، اطلاعات لازم را می‌گیرد و HTTPS را راه‌اندازی می‌کند. هنگام توقف، **IP را در بیت‌پین ثبت کنید**؛ در پایان **آدرس محرمانه را در ChatGPT و Claude اضافه کنید**. تنظیم DNS و تأییدهای داخل حساب‌ها را باید خودتان انجام دهید. اگر پیش‌نیازها آماده نیستند یا بار اول است نصب می‌کنید، مراحل زیر را دنبال کنید. برای نصب موجود، در پوشهٔ پروژه `bash install.sh` را اجرا کنید؛ دریافت دوبارهٔ ریپو لازم نیست.

## نصب قدم‌به‌قدم روی سرور

این راهنما برای **Ubuntu/Debian با دامنهٔ عمومی** و نصب پیش‌فرض با **آدرس محرمانه** است. سرور باید به بیت‌پین دسترسی داشته باشد و از اینترنت برای ChatGPT و Claude قابل دسترسی باشد. کلید API بیت‌پین در مرحلهٔ ۴ آماده می‌شود؛ برای اتصال از داخل ChatGPT و Claude به کلید OpenAI یا Anthropic نیاز ندارید.

[۱. دامنه](#fa-domain) · [۲. ورود به سرور](#fa-ssh) · [۳. نصب](#fa-install) · [۴. ثبت IP در بیت‌پین](#fa-bitpin-ip) · [۵. تنظیمات](#fa-setup) · [۶. ChatGPT](#fa-chatgpt) · [۷. Claude](#fa-claude) · [۸. تست اتصال](#fa-test)

<a id="fa-domain"></a>

### ۱. دامنه را به سرور وصل کنید

فرض کنیم آدرس اتصال `mcp.example.com` باشد. در پنل DNS دامنه، این رکورد را بسازید و `example.com` را با دامنهٔ خود جایگزین کنید:

| گزینه | مقدار |
|---|---|
| Type | `A` |
| Name | `mcp` |
| Value | IP عمومی ورودی سرور |

اگر رکورد `AAAA` دارید، باید به IPv6 صحیح همین سرور اشاره کند. پورت‌های **TCP 80 و 443** را در فایروال سرور و پنل ارائه‌دهنده باز کنید و دسترسی SSH را حفظ کنید. نصب پیش‌فرض این دو پورت را استفاده می‌کند؛ اگر Nginx یا وب‌سرور دیگری آن‌ها را گرفته، ابتدا [تنظیم پراکسی موجود](#fa-troubleshooting) را بررسی کنید.

<a id="fa-ssh"></a>

### ۲. وارد سرور شوید

در ترمینال کامپیوتر خود اجرا کنید؛ نام کاربری و IP واقعی سرور را جایگزین کنید:

</div>

```bash
ssh USER@SERVER_IP
```

<div dir="rtl">

از اینجا به بعد دستورها داخل سرور اجرا می‌شوند. ابزارهای اولیه را نصب کنید:

</div>

```bash
sudo apt update
sudo apt install -y git curl ca-certificates
```

<div dir="rtl">

اگر با کاربر `root` وارد شده‌اید و `sudo` نصب نیست، دستورهای بالا را بدون `sudo` اجرا کنید.

<a id="fa-install"></a>

### ۳. پروژه را دریافت و نصب‌کننده را اجرا کنید

ریپو عمومی است؛ برای دریافت کد به ورود GitHub یا توکن نیاز ندارید.

</div>

```bash
cd ~
git clone https://github.com/Erfouni/bitpin-ai-connector.git
cd bitpin-ai-connector
bash install.sh
```

<div dir="rtl">

اگر Docker نصب نباشد، نصب‌کننده نصب آن با اسکریپت رسمی Docker را پیشنهاد می‌کند؛ برای ادامه `Y` بزنید. حداقل Docker Compose نسخهٔ **2.30** لازم است. ساخت برنامه ممکن است چند دقیقه طول بکشد.

سپس نصب‌کننده IP خروجی سرور را نشان می‌دهد و منتظر می‌ماند:

</div>

```text
SERVER PUBLIC OUTBOUND IP · IP مجاز بیت‌پین
  IPV4: <detected-public-ipv4>
  IPV6: <detected-public-ipv6-or-unavailable>

After adding the displayed outbound IP in Bitpin, press Enter to continue:
```

<div dir="rtl">

مقدارهای داخل `<...>` در این نمونه توضیحی‌اند؛ نصب‌کننده IP واقعی یا پیام عدم دسترسی را نشان می‌دهد. **هنوز Enter نزنید؛ ابتدا مرحلهٔ ۴ را انجام دهید.**

<a id="fa-bitpin-ip"></a>

### ۴. IP را در بیت‌پین ثبت و کلید API را آماده کنید

1. در مرورگر وارد حساب بیت‌پین و بخش **مدیریت API / کلیدهای API** شوید. عنوان دقیق منو ممکن است در نسخهٔ فعلی سایت متفاوت باشد.
2. کلیدی مخصوص این اتصال، مثلاً با نام `Bitpin AI Connector`، بسازید یا کلید موردنظر را ویرایش کنید.
3. عدد واقعی نمایش‌داده‌شده مقابل `IPV4` را در **IPهای مجاز** همان کلید وارد کنید.
4. دسترسی **مشاهدهٔ حساب و سفارش‌ها** و برای خریدوفروش، **معامله و مدیریت سفارش** را فعال کنید. مجوز برداشت لازم نیست.
5. اگر IPv6 هم نمایش داده شد و اتصال از آن استفاده می‌کند، آن مسیر نیز باید در محدودیت IP مجاز باشد.
6. تنظیمات را ذخیره و تأییدهای درخواستی بیت‌پین را تکمیل کنید. **API Key و Secret Key** را برای مرحلهٔ بعد آماده نگه دارید.
7. به ترمینال سرور برگردید و Enter بزنید.

**IP عمومی خروجی همین سرور را ثبت کنید.** IP لپ‌تاپ، IP داخلی Docker مثل `172.x.x.x` و نام دامنه جای آن نیستند. در سرورهای پشت NAT، IP خروجی ممکن است با IP ورودی استفاده‌شده در DNS فرق داشته باشد. پس از جابه‌جایی سرور یا تغییر IP، فهرست مجاز را به‌روز کنید.

تشخیص IP از داخل کانتینر با سرویس [ipify](https://www.ipify.org/) و بدون ارسال کلیدهای بیت‌پین انجام می‌شود. اگر تشخیص ناموفق بود، IP خروجی را از ارائه‌دهندهٔ سرور بگیرید؛ برنامه IP حدسی نمی‌دهد. در مسیریابی وابسته به مقصد، IP مشاهده‌شده توسط بیت‌پین ممکن است متفاوت باشد؛ تست `doctor --private` دسترسی واقعی به بیت‌پین را بررسی می‌کند.

<a id="fa-setup"></a>

### ۵. سؤال‌های نصب‌کننده را پاسخ دهید

| سؤال | پاسخ |
|---|---|
| `Domain` | مثل `mcp.example.com`؛ بدون `https://` و بدون `/` |
| `Email for TLS certificate notices` | ایمیل شما برای گواهی HTTPS |
| `Bitpin API key` | کلید API بیت‌پین |
| `Bitpin secret key` | کلید Secret بیت‌پین |
| `Enable REAL order placement and cancellation? [Y/n]` | `Y` یا Enter برای معاملهٔ واقعی؛ `n` برای فقط مشاهده |

هنگام واردکردن کلیدها چیزی روی صفحه نمایش داده نمی‌شود؛ طبیعی است. نصب‌کننده سرویس و HTTPS خودکار را راه‌اندازی می‌کند و دسترسی خواندن حساب و HTTPS را **بدون ثبت معامله** بررسی می‌کند. پس از موفقیت، آدرس کامل اتصال را نشان می‌دهد:

</div>

```text
https://mcp.example.com/mcp-<random-secret>
```

<div dir="rtl">

**همان روش سادهٔ [Mizito AI Connector](https://github.com/Erfouni/mizito-ai-connector):** آدرس کامل حکم رمز دسترسی را دارد. آن را فقط در تنظیمات connector وارد کنید، نه در چت، issue، تصویر یا لینک عمومی. صفحهٔ عمومی دامنه مسیر محرمانه را نمایش نمی‌دهد. این روش نشست و مجوز جداگانه برای هر مدل ندارد؛ هر دارندهٔ آدرس به ابزارهای فعال دسترسی دارد. OAuth هم در ادامه به‌صورت اختیاری توضیح داده شده است.

در مراحل ۶ و ۷ دقیقاً آدرس تولیدشده را کپی کنید؛ نمونهٔ بالا را وارد نکنید و مسیر تصادفی را به `/mcp` تغییر ندهید. کلید بیت‌پین فقط روی سرور وارد می‌شود و نباید در فرم اتصال مدل قرار گیرد.

<a id="fa-chatgpt"></a>

### ۶. اتصال به ChatGPT

1. [ChatGPT Plugins](https://chatgpt.com/plugins) را باز کنید؛ `+` و **Add custom MCP server** را بزنید.
2. نام را `Bitpin` و Server URL را **آدرس کامل محرمانه** بگذارید.
3. Authentication را **No authentication** انتخاب کنید؛ اعتبار دسترسی در خود آدرس است.
4. توضیحات دسترسی را بررسی و **Create as a plugin** را انتخاب کنید.
5. پلاگین را نصب کنید؛ در چت جدید `@` بنویسید و `Bitpin` را انتخاب کنید.

مسیر منوها و دسترسی ممکن است با حساب یا workspace متفاوت باشد. [راهنمای رسمی OpenAI](https://developers.openai.com/plugins/build/app-quickstart#connect-your-mcp-server-in-chatgpt).

<a id="fa-claude"></a>

### ۷. اتصال به Claude

1. در **Customize → Connectors**، گزینهٔ `+ Add` و **Add custom connector** را بزنید.
2. نام `Bitpin` و **آدرس کامل محرمانه** را وارد کنید و `Continue` بزنید.
3. Authentication را **No sign in** بگذارید؛ OAuth و Request headers را خالی بگذارید.
4. با `Add` ذخیره کنید؛ در چت از `+ → Connectors`، اتصال Bitpin را روشن کنید.

در حساب سازمانی، افزودن اولیه ممکن است به دسترسی مدیر نیاز داشته باشد. [راهنمای رسمی Claude](https://support.claude.com/en/articles/11175166-get-started-with-custom-connectors-using-remote-mcp).

<a id="fa-test"></a>

### ۸. اتصال را بدون معامله امتحان کنید

ابتدا در هر مدل، با اتصال Bitpin فعال، بنویسید:

> با اتصال Bitpin وضعیت اتصال و قیمت BTC_IRT را بررسی کن. هیچ سفارشی ثبت نکن.

سپس برای بررسی دسترسی حساب:

> موجودی کیف پول و سفارش‌های باز من را از بیت‌پین بگیر و نشان بده. هیچ تغییری ایجاد نکن.

دریافت پاسخ موفق برای هر دو، دسترسی بازار و حساب را بررسی می‌کند. با فعال‌بودن معامله در مرحلهٔ ۵، ابزار خرید، فروش و لغو سفارش نیز قابل استفاده است. محدودیت‌ها و تأییدهای خود ChatGPT و Claude مستقل از این سرور هستند؛ فعال‌بودن ابزار معامله تضمین اجرای هر دستور توسط مدل نیست.

برای بررسی وضعیت، داخل پوشهٔ پروژه روی سرور اجرا کنید:

</div>

```bash
docker compose ps
docker compose exec connector bitpin-ai-connector doctor --private
docker compose logs --tail 100
```

<div dir="rtl">

اگر Docker خطای permission denied داد، دستور را با `sudo docker ...` اجرا کنید. خطای دسترسی بیت‌پین را با بررسی IP مجاز، کلیدها و مجوزهای API پیگیری کنید؛ برای خطای HTTPS، DNS، رکورد AAAA، پورت‌ها و لاگ Caddy را بررسی کنید. جزئیات در [عیب‌یابی](#fa-troubleshooting) آمده است.

برای نمایش دوبارهٔ IP خروجی **سرویس در حال اجرا** و آدرس محرمانه:

</div>

```bash
docker compose exec connector bitpin-ai-connector ip
docker compose exec connector bitpin-ai-connector url
```

<div dir="rtl">

اجرای دوبارهٔ `bash install.sh` تنظیمات موجود را حفظ می‌کند و کلیدها را دوباره نمی‌پرسد. برای بررسی اولیهٔ IP قبل از نصب Docker نیز می‌توانید `curl -4 https://api.ipify.org` و در صورت داشتن IPv6، `curl -6 https://api6.ipify.org` را اجرا کنید؛ مرجع نهایی، مسیر خروجی کانتینر و پذیرش اتصال توسط بیت‌پین است.

## ابزارها

| بخش | ابزارهای MCP |
|---|---|
| وضعیت و مشخصات بازار | `connector_status`, `list_markets`, `list_currencies`, `list_networks` |
| قیمت و نقدشوندگی | `get_tickers`, `get_orderbook`, `get_recent_trades` |
| کندل و تحلیل | `get_candles`, `analyze_market` |
| حساب و کارمزد | `get_wallets`, `get_commissions` |
| سفارش و معاملات انجام‌شده | `list_orders`, `get_order`, `get_order_history`, `get_fills` |
| پیش‌نمایش و ثبت | `preview_order`, `place_order`, `place_orders` |
| پیگیری نتیجه | `resolve_order`, `get_order_receipt` |
| لغو | `cancel_order`, `cancel_orders` |

۲۲ ابزار، منبع `bitpin://guide` و prompt آمادهٔ `market_review` ارائه می‌شود. اطلاعات ورودی همهٔ ابزارها از طریق MCP به مدل معرفی می‌شوند.

سفارش‌های **Market، Limit، Stop Limit و OCO** در هر دو سمت خرید و فروش پشتیبانی می‌شوند. تحلیل شامل RSI14، SMA20، EMA12/26، MACD12/26/9، Bollinger20/2، ATR14، بازده و عمق دفتر سفارش است. این محاسبات توصیف داده‌اند؛ موتور پیش‌بینی یا تصمیم‌گیر مستقل نیستند.

انتقال وجه، برداشت، تغییر حساب و مدیریت کلید API ابزار ندارند.

## قرارداد سفارش

مبلغ و قیمت باید **رشتهٔ عدد اعشاری** باشند، بدون جداکننده یا نمایش علمی؛ مثلاً `"0.001"`. نماد و دقت مجاز را از `list_markets` بگیرید. سرور عدد را خودکار گرد نمی‌کند. محدودیت حداقل مبلغ، موجودی و پذیرش نهایی را بیت‌پین اعمال می‌کند.

| نوع | فیلدهای مقدار و قیمت |
|---|---|
| `market` | دقیقاً یکی از `base_amount` یا `quote_amount` |
| `limit` | `base_amount` و `price` |
| `stop_limit` | `base_amount`، `price` و `stop_price` |
| `oco` | `base_amount`، `price`، `stop_price` و `price_limit_oco` |

مثال ورودی `preview_order`؛ همین ساختار برای `place_order` معاملهٔ واقعی می‌سازد:

</div>

```json
{
  "order": {
    "symbol": "BTC_IRT",
    "side": "buy",
    "type": "market",
    "quote_amount": "100000",
    "identifier": "my-btc-buy-20261010-001"
  }
}
```

<div dir="rtl">

برای هر قصد سفارش، `identifier` یکتای ثابت بدهید. درخواست قبل از ارسال در SQLite ثبت می‌شود. تکرار همان شناسه در همان پایگاه داده سفارش دیگری ارسال نمی‌کند؛ تغییر مبلغ با همان شناسه رد می‌شود. تعویض API Key یا دامنهٔ رسمی API، دفتر ثبت سفارش‌ها را از بین نمی‌برد.

- `accepted` / `existing`: سفارش پذیرفته یا قبلاً پیدا شده؛ لزوماً انجام نشده است. با `get_order` وضعیت زنده را بخوانید.
- `unknown`: ممکن است درخواست به بیت‌پین رسیده باشد. با `resolve_order` و تاریخچه پیگیری کنید؛ با شناسهٔ تازه جایگزین نفرستید.
- `rejected` / `not_sent`: پاسخ رد قطعی یا عدم ارسال ثبت شده است؛ علت را بررسی کنید.
- لغو سفارش ناهمگام است؛ پاسخ `cancel_requested` مانع انجام‌شدن بخشی از سفارش در فاصلهٔ درخواست تا لغو نیست.

ارسال و لغو گروهی به ترتیب اجرا می‌شوند و **اتمیک نیستند**. ثبت گروهی حداکثر ۱۰ سفارش دارد و در اولین نتیجهٔ نامطمئن یا ناموفق متوقف می‌شود؛ سفارش‌های قبلی باقی می‌مانند. لغو گروهی حداکثر ۵۰ شناسهٔ مشخص می‌گیرد.

هر نصب برای **یک حساب بیت‌پین** است. برای تعویض کلید همان حساب، داده‌ها را حفظ کنید؛ برای حساب دیگری نصب و volume جدا بسازید. پاک‌کردن volume، بازیابی نسخهٔ پشتیبان قدیمی یا اجرای دو نصب با پایگاه دادهٔ جدا، تضمین محلی جلوگیری از تکرار را از بین می‌برد. خود شناسهٔ بیت‌پین را تضمین همیشگی عدم تکرار فرض نکنید.

## واحد، زمان و محدودیت داده

- `IRT` در بازار تومان است. موجودی با نام `RIAL` بدون تبدیل حدسی برگردانده می‌شود. `balance` موجودی قابل استفاده است و `frozen` جداست؛ دوباره از balance کم نکنید.
- زمان ورودی کندل **Unix seconds** است؛ تاریخچهٔ سفارش **Unix milliseconds**. بازهٔ تاریخچه حداکثر سه ماه است.
- تایم‌فریم‌ها: `1m 5m 15m 30m 1h 3h 4h 6h 1d 1w 1M`. حرف بزرگ M ماه است. هر درخواست کندل حداکثر ۱۰هزار ردیف.
- تحلیل فقط کندل بسته‌شده را مصرف می‌کند، فاصله‌های گمشده را گزارش می‌کند و در صورت دادهٔ ناکافی اندیکاتور را `null` می‌دهد.
- دفتر سفارش تا ۲۰ سطح دارد؛ تخمین اجرا فقط همان عمق را پوشش می‌دهد، کارمزد ندارد و تضمین قیمت یا موجودی نیست. مقادیر کارمزد به همان واحد خام API برمی‌گردند.
- فهرست‌ها یک صفحه می‌دهند. `next_offset` یا `next_cursor` را با همان فیلترها ادامه دهید. سفارش بسته در فهرست جاری فقط هفت روز می‌ماند؛ تاریخچهٔ قدیمی مخصوص سفارش‌های دارای معامله است و ممکن است با تأخیر به‌روز شود.

## مدیریت سرور

</div>

```bash
docker compose ps
docker compose logs --tail 100
docker compose exec connector bitpin-ai-connector doctor --private
docker compose restart
```

<div dir="rtl">

به‌روزرسانی: `git pull --ff-only` و سپس `bash install.sh`. توقف با حفظ داده: `docker compose down`، **بدون `-v`**.

برای غیرفعال‌کردن معامله، در `.env` مقدار `TRADING_ENABLED=false` بگذارید و `docker compose up -d --force-recreate connector` اجرا کنید. این کار سفارش‌های فعال قبلی را لغو نمی‌کند.

کلیدها در `.secrets.env` با فرمت خام `KEY=value` ذخیره می‌شوند. فایل را source نکنید و دور مقدارها quote نگذارید؛ علامت‌های `$` و `#` بخشی از مقدار هستند. تنظیمات و داده‌ها از Git و image Docker کنار گذاشته شده‌اند.

**تعویض آدرس محرمانه:** `bash install.sh --rotate-url` فقط مسیر دسترسی را عوض می‌کند و سرویس را بازسازی می‌کند. آدرس جدید را در هر دو مدل جایگزین کنید. آدرس قبلی دیگر کار نمی‌کند و سابقهٔ سفارش‌ها حفظ می‌شود.

### پشتیبان‌گیری

پایگاه داده شامل دفتر سفارش‌ها و اطلاعات ورود است. با API پشتیبان‌گیری SQLite یک نسخهٔ سازگار تهیه کنید:

</div>

```bash
docker compose exec connector python -c "import sqlite3; a=sqlite3.connect('/data/connector.sqlite3'); b=sqlite3.connect('/data/backup.sqlite3'); a.backup(b); b.close(); a.close()"
docker compose cp connector:/data/backup.sqlite3 ./connector-backup.sqlite3
chmod 600 connector-backup.sqlite3
```

<div dir="rtl">

فایل پشتیبان، `.env` و `.secrets.env` را خصوصی و ترجیحاً رمزگذاری‌شده نگه دارید. برای بازیابی، ابتدا connector را متوقف کنید، پایگاه داده را داخل همان volume به مسیر `/data/connector.sqlite3` بازگردانید و مالکیت `10001:10001` و مجوز `600` را حفظ کنید. پیش از فعال‌کردن معامله، سفارش‌های بعد از زمان backup را با حساب تطبیق دهید.

## OAuth اختیاری

اگر به ورود با رمز و مجوزهای جداگانه نیاز دارید، **در نصب تازه** به‌جای دستور معمول، `bash install.sh --oauth` اجرا کنید. رمز اتصال را انتخاب می‌کنید و آدرس MCP ثابت `https://your-domain/mcp` خواهد بود. در ChatGPT و Claude روش OAuth را انتخاب کنید؛ ثبت خودکار کلاینت پشتیبانی می‌شود. کلید بیت‌پین را در فرم ورود مدل یا صفحهٔ اجازه وارد نکنید.

OAuth شامل S256 PKCE، محدودیت callback به دامنه‌های مشخص، بررسی resource، سطح دسترسی `bitpin:read` / `bitpin:trade`، توکن دسترسی یک‌ساعته، چرخش refresh token و ابطال خانوادهٔ توکن هنگام استفادهٔ مجدد است. عمر grant حداکثر ۳۰ روز است. رمز ورود به‌صورت scrypt ذخیره می‌شود. تلاش‌های ورود محدودند.

تغییر کلیدهای API باطل‌کردن نشست‌های مدل نیست. برای ابطال همهٔ نشست‌های OAuth:

</div>

```bash
docker compose exec connector bitpin-ai-connector revoke-sessions
```

<div dir="rtl">

توکن ثابت اختیاری `CONNECTOR_API_TOKEN` جداست؛ برای ابطال آن مقدار را در فایل secrets تعویض و connector را بازسازی کنید. این توکن فقط در حالت OAuth کاربرد دارد. در حالت آدرس محرمانه، از `--rotate-url` استفاده کنید.

نصب‌کننده برای حفظ تنظیمات، حالت ورود یک نصب موجود را با `--oauth` عوض نمی‌کند. برای تغییر دستی، `AUTH_MODE=oauth` در `.env` و هش رمز در secrets تنظیم کنید؛ هش را بدون نوشتن رمز در تاریخچهٔ shell با دستور زیر بسازید، سپس connector را بازسازی کنید:

</div>

```bash
docker compose run --rm --no-deps connector python -c "import getpass; from bitpin_connector.auth import hash_password; print(hash_password(getpass.getpass('Connector password: ')))"
```

<div dir="rtl">

در صورت تغییر دامنهٔ callback یک کلاینت معتبر، `OAUTH_REDIRECT_ORIGINS` را به‌صورت آرایهٔ JSON از originهای دقیق HTTPS در `.secrets.env` قرار دهید. هیچ wildcard یا جست‌وجوی زیررشته‌ای پذیرفته نمی‌شود.

## اجرای محلی

Python 3.12 یا جدیدتر و [uv](https://docs.astral.sh/uv/) لازم است:

</div>

```bash
uv sync --frozen
uv run python scripts/setup.py --local
uv run bitpin-ai-connector serve --transport stdio
```

<div dir="rtl">

برای Claude Desktop از [نمونهٔ تنظیمات](examples/claude-desktop.json) و برای Codex از [نمونهٔ TOML](examples/codex.toml) استفاده کنید؛ مسیرها را مطلق کنید. در ویندوز executable داخل `.venv\Scripts\bitpin-ai-connector.exe` است. پروتکل stdio از stdout استفاده می‌کند؛ لاگ به stderr می‌رود. دسترسی محلی تحت مجوزهای سیستم‌عامل است.

برای HTTP محلی، `serve --transport http` را اجرا کنید. آدرس localhost برای اتصال سرویس ابری ChatGPT یا Claude قابل دسترسی نیست؛ آن‌ها به دامنهٔ عمومی HTTPS نیاز دارند.

## استفاده از API مدل‌ها

[نمونهٔ OpenAI Responses](examples/openai_api.py) و [نمونهٔ Claude Messages](examples/claude_api.py) بدون کتابخانهٔ اضافی ارائه شده‌اند. `BITPIN_MCP_URL` و نام مدل مورد دسترسی‌تان (`OPENAI_MODEL` یا `ANTHROPIC_MODEL`) و کلید همان سرویس را در محیط اجرای نمونه تنظیم کنید. در حالت OAuth، `CONNECTOR_API_TOKEN` را هم بدهید؛ در حالت مسیر محرمانه آن را حذف کنید.

این نمونه‌ها فراخوانی پولی API هستند و فقط سه ابزار عمومی خواندنی را فعال می‌کنند. برای افزودن ابزار معامله، فهرست مجاز را آگاهانه توسعه دهید و سیاست تأیید در برنامهٔ خود قرار دهید. کلید بیت‌پین فقط روی connector می‌ماند. [مستندات OpenAI](https://developers.openai.com/api/docs/guides/tools-connectors-mcp) و [مستندات Claude](https://platform.claude.com/docs/en/agents-and-tools/mcp-connector).

<a id="fa-troubleshooting"></a>

## جزئیات استقرار و عیب‌یابی

کانتینر برنامه با کاربر غیر root، فایل‌سیستم فقط‌خواندنی و volume مجزا اجرا می‌شود. فقط Caddy پورت عمومی دارد. access log خام فعال نیست؛ URI و هدرهای حساس از لاگ ساختاریافتهٔ Caddy حذف/پوشانده می‌شوند. اگر CDN یا پراکسی دیگری اضافه می‌کنید، ثبت مسیر محرمانه را آنجا هم خاموش یا ماسک کنید.

اگر پورت 80/443 از قبل در اختیار وب‌سرور دیگری است، compose پیش‌فرض را هم‌زمان روی همان پورت‌ها اجرا نکنید. سرویس Caddy را کنار بگذارید و پراکسی موجود را با حفظ Host، HTTPS و پشتیبانی Streamable HTTP به connector متصل کنید. مستقیماً پورت 8000 را روی اینترنت باز نکنید.

| مشکل | بررسی |
|---|---|
| clone ناموفق است | آدرس عمومی ریپو، DNS و دسترسی HTTPS به GitHub را بررسی کنید؛ ورود یا توکن لازم نیست |
| TLS یا check-https ناموفق | DNS و AAAA، فایروال، پورت‌های 80/443، لاگ Caddy و دسترسی مرجع صدور گواهی |
| اتصال مدل پیدا نمی‌شود | آدرس کامل شامل مسیر تصادفی و دسترسی اینترنتی سرور؛ در حالت ساده No authentication |
| بیت‌پین 401/403 | اعتبار API Key/Secret، مجوزها و IP خروجی مجاز |
| معامله disabled است | TRADING_ENABLED و بازسازی container |
| خطای bitpin:trade | در حالت OAuth دسترسی معامله را در اتصال مدل تأیید کنید |
| خطای 429 یا بودجهٔ ورود | تا پایان cooldown یا پنجرهٔ محدودیت صبر کنید؛ restart محدودیت را پاک نمی‌کند |
| نتیجهٔ سفارش unknown | همان identifier را پیگیری کنید؛ سفارش جایگزین خودکار ارسال نکنید |

کلیدهای ثابت و tokenهای بیت‌پین در فایل/SQLite خصوصی سرور نگهداری می‌شوند؛ رمزگذاری مستقل در حالت سکون وجود ندارد. دسترسی مدیریتی به سرور یا volume، دسترسی به حساب متصل است.

## توسعه و اعتبارسنجی

</div>

```bash
uv sync --frozen
uv run pytest -q
uv run ruff check .
uv run ruff format --check .
docker build -t bitpin-ai-connector:local .
```

<div dir="rtl">

تست‌ها شامل پروتکل واقعی MCP روی stdio و HTTP، مسیر محرمانه، OAuth/PKCE/CSRF و ابطال توکن، سفارش هم‌زمان و پس از restart/تعویض کلید، قطع ارتباط پس از ارسال، اعداد دقیق، کندل ناقص و حفظ اسرار در نصب مجدد هستند. CI لینوکس تست، lint و ساخت Docker را اجرا می‌کند.

اتصال خصوصی به حساب، ثبت سفارش واقعی، اتصال از حساب واقعی ChatGPT/Claude و صدور گواهی دامنهٔ شما به اطلاعات استقرار نیاز دارند و در توسعه به‌عنوان «تست‌شده روی حساب واقعی» ادعا نشده‌اند. نصب‌کننده اتصال خواندنی حساب و HTTPS را روی سرور شما بررسی می‌کند.

[قرارداد API و منابع](docs/api-contract.md) · [طرح فنی](docs/design.md)

پروژهٔ مستقل و غیررسمی است و وابستگی سازمانی به Bitpin، OpenAI یا Anthropic ندارد. مجوز کد MIT است؛ فونت Vazirmatn با مجوز OFL همراه پروژه توزیع می‌شود.

</div>
