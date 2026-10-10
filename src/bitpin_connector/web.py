from html import escape

from .config import Settings


def render_page(settings: Settings, *, pending=None, ticket="", csrf="", error="") -> str:
    simple = settings.auth_mode == "secret_path"
    endpoint = escape(settings.public_url + "/mcp-…" if simple else settings.resource_url)
    badge = ("HTTPS" if settings.public_url.startswith("https:") else "LOCAL") + (
        " / Secret URL" if simple else " / OAuth"
    )
    address_step = (
        "آدرس محرمانه‌ای را که نصب‌کننده نمایش داد وارد کنید و No authentication را انتخاب کنید."
        if simple
        else "آدرس بالا را وارد و ورود با OAuth را انتخاب کنید."
    )
    final_step = (
        "اتصال را در گفت‌وگو روشن کنید. آدرس کامل فقط در ترمینال سرور قابل دریافت است."
        if simple
        else "با رمز اتصال سرور وارد شوید و دسترسی دستیار را تأیید کنید."
    )
    error_html = f'<div class="error" role="alert">{escape(error)}</div>' if error else ""
    if pending:
        name = escape(pending["client_name"])
        callback = escape(pending["params"]["redirect_uri"])
        has_trade = "bitpin:trade" in pending["params"]["scopes"]
        permissions = (
            "مشاهدهٔ دارایی و بازار، ثبت خرید و فروش و لغو سفارش"
            if has_trade
            else "مشاهدهٔ دارایی، سفارش‌ها و اطلاعات بازار"
        )
        content = f'''<span class="eyebrow">تأیید اتصال</span><h1>حساب شما،<br><em>دستیار شما.</em></h1>
        <p class="lead">برنامهٔ <b dir="auto">{name}</b> برای اتصال به حساب بیت‌پین شما درخواست دسترسی دارد.</p>
        <div class="permission"><span class="dot"></span><div><strong>دسترسی درخواستی</strong><p>{permissions}</p></div></div>
        <p class="caption">مقصد بازگشت را بررسی کنید؛ نام برنامه توسط درخواست‌کننده تعیین می‌شود.</p><code class="callback" dir="ltr">{callback}</code>
        {error_html}<form method="post" action="/login"><input type="hidden" name="ticket" value="{escape(ticket)}"><input type="hidden" name="csrf" value="{escape(csrf)}">
        <label for="password">رمز اتصال سرور</label><input id="password" name="password" type="password" autocomplete="current-password" maxlength="256" required placeholder="رمزی که هنگام نصب انتخاب کردید">
        <p class="caption">کلید بیت‌پین را اینجا وارد نکنید. این رمز فقط برای اجازهٔ اتصال است.</p>
        <div class="actions"><button class="primary" name="decision" value="approve">تأیید و اتصال <span aria-hidden="true">←</span></button><button class="secondary" name="decision" value="deny" formnovalidate>انصراف</button></div></form>'''
    else:
        content = f"""<span class="eyebrow">آمادهٔ اتصال</span><h1>بیت‌پین،<br><em>در گفت‌وگوی شما.</em></h1>
        <p class="lead">دارایی‌ها و بازار را بررسی کنید، تحلیل بگیرید و سفارش‌های خود را با دستیار دلخواه مدیریت کنید.</p>
        {error_html}<div class="endpoint"><div><span>آدرس اتصال MCP</span><span class="badge">{badge}</span></div><code dir="ltr">{endpoint}</code></div>
        <ol class="steps"><li><span>۱</span><div><strong>افزودن اتصال</strong><p>در تنظیمات ChatGPT یا Claude، یک اتصال MCP جدید بسازید.</p></div></li>
        <li><span>۲</span><div><strong>وارد کردن آدرس</strong><p>{address_step}</p></div></li>
        <li><span>۳</span><div><strong>شروع گفت‌وگو</strong><p>{final_step}</p></div></li></ol>"""
    return f"""<!doctype html><html lang="fa" dir="rtl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Bitpin AI Connector · اتصال بیت‌پین</title><link rel="stylesheet" href="/assets/style.css"><link rel="icon" href="data:,"></head>
    <body><div class="shell"><header><a class="brand" href="/" aria-label="صفحهٔ اصلی"><span class="brandmark" aria-hidden="true">b<span>↗</span></span><span dir="ltr">bitpin <b>ai connector</b></span></a><span class="status"><i></i> اتصال امن</span></header>
    <main><section class="content">{content}</section><aside aria-label="قابلیت‌های اتصال"><div class="orb"><span class="orbit orbit-a"></span><span class="orbit orbit-b"></span><div class="core">b<span>↗</span></div><span class="node node-a">GPT</span><span class="node node-b">Claude</span><span class="node node-c">MCP</span></div>
    <div class="aside-caption"><span class="eyebrow">یک اتصال · انتخاب با شما</span><h2>از دادهٔ بازار<br>تا اجرای سفارش.</h2><p>کلیدهای بیت‌پین روی سرور شما می‌مانند.<br>دسترسی دستیار با اجازهٔ شما برقرار می‌شود.</p></div><div class="tags"><span>بازار و تحلیل</span><span>دارایی‌ها</span><span>خرید و فروش</span></div></aside></main>
    <footer><span dir="ltr">BITPIN AI CONNECTOR</span><span>اتصال مستقل · میزبانی روی سرور شما</span></footer></div></body></html>"""
