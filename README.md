# Bitpin AI Connector

[![Tests](https://github.com/Erfouni/bitpin-ai-connector/actions/workflows/tests.yml/badge.svg)](https://github.com/Erfouni/bitpin-ai-connector/actions/workflows/tests.yml)

<div dir="rtl">

اتصال مستقیم **بیت‌پین به ChatGPT، Claude و کلاینت‌های MCP** برای مشاهدهٔ دارایی، تحلیل بازار، ثبت خرید و فروش و مدیریت سفارش‌ها.

این پروژه مستقل از AI Trader است: تصمیم از گفت‌وگوی شما با مدل می‌آید و این سرور ابزار اتصال را فراهم می‌کند. استراتژی، زمان‌بند معامله یا وابستگی به ربات ندارد. برای نصب، **کلید OpenAI یا Anthropic لازم نیست**.

## نصب سریع روی سرور

یک سرور لینوکس، دامنه‌ای مثل `mcp.example.com` و کلید API بیت‌پین لازم دارید. DNS دامنه باید به سرور اشاره کند؛ پورت‌های TCP 80 و 443 آزاد و از اینترنت قابل دسترسی باشند. اگر رکورد AAAA دارید، IPv6 آن هم باید درست باشد. سرور باید هم به بیت‌پین دسترسی داشته باشد و هم از سمت OpenAI و Anthropic قابل دسترسی باشد.

پس از ورود SSH به سرور:

</div>

```bash
git clone https://github.com/Erfouni/bitpin-ai-connector.git
cd bitpin-ai-connector
bash install.sh
```

<div dir="rtl">

ریپو خصوصی است؛ Git روی سرور باید به حساب GitHub شما دسترسی داشته باشد. در صورت تنظیم SSH، آدرس clone می‌تواند `git@github.com:Erfouni/bitpin-ai-connector.git` باشد. کلید GitHub را داخل فایل تنظیمات این پروژه نگذارید.

نصب‌کننده:

1. در صورت نبود Docker، نصب آن با اسکریپت رسمی Docker را پیشنهاد می‌کند.
2. ابتدا IP عمومی خروجی سرور (IPv4 و در صورت دسترسی IPv6) را نشان می‌دهد و منتظر می‌ماند تا آن را در IPهای مجاز کلید بیت‌پین ثبت کنید. سپس دامنه، ایمیل گواهی HTTPS، API Key و Secret Key را می‌پرسد؛ کلیدها مخفی‌اند.
3. فعال بودن خرید، فروش و لغو سفارش واقعی را می‌پرسد؛ پیش‌فرض «بله» است.
4. سرویس و HTTPS خودکار را راه‌اندازی می‌کند؛ اتصال عمومی و دسترسی خواندن حساب را بدون معامله بررسی می‌کند.
5. یک آدرس محرمانه مثل زیر نمایش می‌دهد.

</div>

```text
https://mcp.example.com/mcp-<random-secret>
```

<div dir="rtl">

**همان روش سادهٔ [Mizito AI Connector](https://github.com/Erfouni/mizito-ai-connector):** آدرس کامل حکم رمز دسترسی را دارد. آن را فقط در تنظیمات connector وارد کنید، نه در چت، issue، تصویر یا لینک عمومی. صفحهٔ عمومی دامنه مسیر محرمانه را نمایش نمی‌دهد. این روش نشست و مجوز جداگانه برای هر مدل ندارد؛ هر دارندهٔ آدرس به ابزارهای فعال دسترسی دارد. OAuth هم در ادامه به‌صورت اختیاری توضیح داده شده است.

قبل از نصب، در تنظیمات کلید بیت‌پین، IP عمومی **خروجی همین سرور** را مجاز کنید و مجوز مشاهده و معامله بدهید. مجوز برداشت لازم نیست. اگر سرور پشت NAT است، IP خروجی ممکن است با IP ورودی فرق کند.

**ثبت IP در بیت‌پین:** وارد مدیریت API حساب بیت‌پین شوید؛ کلید موردنظر را بسازید یا ویرایش کنید و عدد نمایش‌داده‌شده کنار `IPV4` را در فهرست IPهای مجاز قرار دهید. اگر IPv6 هم نمایش داده شد و مسیر اتصال شما از آن استفاده می‌کند، آن مسیر هم باید مجاز باشد. IP داخلی Docker مثل `172.x.x.x`، IP لپ‌تاپ و نام دامنه جای IP عمومی خروجی سرور نیستند. سپس به ترمینال برگردید و Enter بزنید تا نصب ادامه یابد.

تشخیص IP از داخل کانتینر و با سرویس [ipify](https://www.ipify.org/)، بدون ارسال کلیدهای بیت‌پین انجام می‌شود. اگر تشخیص ناموفق بود، برنامه IP حدسی نشان نمی‌دهد؛ IP خروجی را از ارائه‌دهندهٔ سرور بگیرید. در مسیریابی یا NAT وابسته به مقصد ممکن است IP مشاهده‌شده توسط بیت‌پین متفاوت باشد؛ تست `doctor --private` مجاز بودن اتصال واقعی بیت‌پین را بررسی می‌کند. پس از انتقال سرور یا تغییر IP، فهرست مجاز را به‌روز کنید.

برای نمایش دوبارهٔ IP از **همان سرویس در حال اجرا**:

</div>

```bash
docker compose exec connector bitpin-ai-connector ip
```

<div dir="rtl">

قبل از نصب Docker، بررسی دستی اولیه هم ممکن است: `curl -4 https://api.ipify.org` و در صورت داشتن IPv6، `curl -6 https://api6.ipify.org`. مرجع نهایی، مسیر خروجی کانتینر و پذیرش احراز هویت توسط بیت‌پین است.

حداقل Docker Compose نسخهٔ 2.30 لازم است. اجرای دوبارهٔ نصب‌کننده تنظیمات موجود را حفظ می‌کند. پس از پایان می‌توانید آدرس را دوباره ببینید:

</div>

```bash
docker compose exec connector bitpin-ai-connector url
```

<div dir="rtl">

## اتصال ChatGPT و Claude

**ChatGPT:** در تنظیمات بخش Apps / Plugins یا Connectors، قابلیت افزودن MCP سفارشی یا Developer mode را فعال کنید. یک اتصال به نام `Bitpin` با آدرس کامل محرمانه بسازید و Authentication را روی **No authentication** بگذارید. سپس اتصال را در گفت‌وگو فعال کنید. عنوان منوها و دسترسی به این قابلیت به حساب و تنظیمات workspace بستگی دارد؛ [راهنمای رسمی](https://developers.openai.com/plugins/build/app-quickstart).

**Claude:** از Settings → Connectors → Add custom connector، آدرس کامل را وارد کنید. تنظیمات OAuth را خالی بگذارید و اتصال را در گفت‌وگو روشن کنید؛ [راهنمای رسمی](https://support.claude.com/en/articles/11175166-get-started-with-custom-connectors-using-remote-mcp).

برای امتحان اولیه بگویید: «وضعیت اتصال بیت‌پین و قیمت BTC_IRT را بررسی کن». بعد می‌توانید موجودی، تحلیل، پیش‌نمایش یا سفارش صریح بخواهید. محدودیت‌ها و تأییدهای خود ChatGPT و Claude مستقل از این سرور هستند؛ فعال بودن ابزار معامله به معنی تضمین اجرای هر دستور توسط پلتفرم میزبان نیست.

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

## جزئیات استقرار و عیب‌یابی

کانتینر برنامه با کاربر غیر root، فایل‌سیستم فقط‌خواندنی و volume مجزا اجرا می‌شود. فقط Caddy پورت عمومی دارد. access log خام فعال نیست؛ URI و هدرهای حساس از لاگ ساختاریافتهٔ Caddy حذف/پوشانده می‌شوند. اگر CDN یا پراکسی دیگری اضافه می‌کنید، ثبت مسیر محرمانه را آنجا هم خاموش یا ماسک کنید.

اگر پورت 80/443 از قبل در اختیار وب‌سرور دیگری است، compose پیش‌فرض را هم‌زمان روی همان پورت‌ها اجرا نکنید. سرویس Caddy را کنار بگذارید و پراکسی موجود را با حفظ Host، HTTPS و پشتیبانی Streamable HTTP به connector متصل کنید. مستقیماً پورت 8000 را روی اینترنت باز نکنید.

| مشکل | بررسی |
|---|---|
| clone خطای 404 می‌دهد | ریپو خصوصی است؛ دسترسی GitHub روی همان سرور را تنظیم کنید |
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
