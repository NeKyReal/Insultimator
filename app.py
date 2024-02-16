import os
from dotenv import load_dotenv, set_key
from flask import Flask, render_template, request, send_from_directory, make_response, url_for, redirect
from logic import change_word_order, generate_insult, generate_nickname, read_json, switch_layout
from rauth import OAuth2Service

app = Flask(__name__)
load_dotenv()
DROPBOX_APP_KEY = os.getenv("DROPBOX_APP_KEY")
DROPBOX_APP_SECRET = os.getenv("DROPBOX_APP_SECRET")
REDIRECT_URI = "https://insultinator.vercel.app/redirect"


# я пишу это после добавления Dropbox, для подобных задач больше не используй
# целее будешь, я серьезно
dropbox = OAuth2Service(
    client_id=DROPBOX_APP_KEY,
    client_secret=DROPBOX_APP_SECRET,
    name="dropbox",
    authorize_url="https://www.dropbox.com/oauth2/authorize",
    access_token_url="https://api.dropbox.com/oauth2/token",
    base_url="https://api.dropbox.com/2/"
)


# обработка ошибки 404
@app.errorhandler(404)
def page_not_found(error):
    return render_template('404.html', name=generate_nickname()), 404


@app.route("/")
def index():
    # есть ли кука с ключом visited
    visited = request.cookies.get("visited")

    if visited:
        # если кука существует, пользователь уже посещал сайт
        return render_template("index.html", name=generate_nickname())
    else:
        # если кука не существует, пользователь посещает сайт впервые
        # устанавливаем куку с ключом visited и значением yes на 24 часа
        response = make_response(render_template("warning.html"))
        response.set_cookie("visited", "yes", max_age=24 * 60 * 60)
        return response


@app.route("/login")
def login():
    redirect_uri = url_for("callback", _external=True)
    params = {"redirect_uri": redirect_uri, "response_type": "code"}
    return redirect(dropbox.get_authorize_url(**params))


@app.route("/callback")
def callback():
    code = request.args.get("code")
    redirect_uri = url_for("callback", _external=True)
    data = {
        "code": code,
        "redirect_uri": redirect_uri,
        "grant_type": "authorization_code",
    }
    response = dropbox.get_raw_access_token(data=data)
    access_token = os.getenv("DROPBOX_ACCESS_TOKEN")

    print(f"[новый access токен: {access_token}]")
    set_key(".env", "DROPBOX_ACCESS_TOKEN", access_token)
    return redirect("/")


@app.route("/favicon.ico")
def favicon():
    return send_from_directory(app.root_path, "static/favicon.ico", mimetype="image/vnd.microsoft.icon")


@app.route("/about")
def about():
    return render_template("about.html", name=generate_nickname())


@app.route("/variations", methods=["POST", "GET"])
def variables():
    variations = None
    if request.method == "POST":
        sentence = request.form["sentence"]
        variations = change_word_order(sentence)
    return render_template("variations.html", variations=variations, name=generate_nickname())


@app.route("/insults", methods=["POST", "GET"])
def insults():
    insult = None
    filename = None
    if request.method == "POST":
        insult, filename = generate_insult()
    return render_template("insults.html", insult=insult, filename=filename, name=generate_nickname())


@app.route("/switch", methods=["POST", "GET"])
def switch():
    sentence = None
    switched_text = None
    if request.method == "POST":
        sentence = request.form["switch-layout"]
        switched_text = switch_layout(sentence)
    return render_template("switch.html", sentence=sentence, switched_text=switched_text, name=generate_nickname())


@app.route("/profile")
def profile():
    return render_template("profile.html", name=generate_nickname())


if __name__ == "__main__":
    app.run(debug=False)
