import configparser
from boxsdk import OAuth2, Client
import webbrowser
from flask import Flask, request, redirect, url_for, render_template
import os
import secrets

# 環境設定ファイルのパスを設定
CONFIG_FILE = 'env.ini'

# ConfigParserオブジェクトを作成
config = configparser.ConfigParser()

# ファイルが存在しない場合はエラーハンドリング
if not os.path.exists(CONFIG_FILE):
    raise FileNotFoundError(f"{CONFIG_FILE} not found.")

# env.iniファイルを読み込む
config.read(CONFIG_FILE)

CLIENT_ID = config['box']['client_id']          #BOX クライアントID
CLIENT_SECRET = config['box']['client_secret']  #BOX クライアントシークレット
REDIRECT_URI = 'http://localhost:5000/callback' #BOX API コールバックURL
FOLDER_ID = config['box']['folder_id']          #BOX アップロード先のフォルダID

#アクセストークン書き込み関数
def store_tokens(access_token, refresh_token):
    config['box']['access_token'] = access_token
    config['box']['refresh_token'] = refresh_token
    with open(CONFIG_FILE, 'w') as configfile:
        config.write(configfile)

#アクセストークン読み込み関数
def read_tokens():
    access_token = config['box'].get('access_token', '')
    refresh_token = config['box'].get('refresh_token', '')
    return access_token, refresh_token

access_token, refresh_token = read_tokens()

#ランダムパスワード生成関数
def generate_password(length=8):
    characters = "23456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
    return ''.join(secrets.choice(characters) for i in range(length))


app = Flask(__name__)

oauth = OAuth2(
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
    store_tokens=store_tokens,
    access_token=access_token,
    refresh_token=refresh_token
)

#Flask / API アクセスページ
if not access_token or not refresh_token:
    @app.route('/')
    def index():
        auth_url, csrf_token = oauth.get_authorization_url(REDIRECT_URI)
        return redirect(auth_url)

    #Flask /callback API コールバックページ
    @app.route('/callback')
    def callback():
        auth_code = request.args.get('code')
        access_token, refresh_token = oauth.authenticate(auth_code)
        return redirect(url_for('upload'))

else:
    oauth.refresh(access_token)

client = Client(oauth)

#Flask /upload ファイルアップロードページ
@app.route('/upload', methods=['GET', 'POST'])
def upload():
    if request.method == 'POST':
        file = request.files['file']
        if file:
            #ファイルを一時フォルダに移動
            file_path = os.path.join('tmp\\', file.filename)
            file.save(file_path)

            # 新しいフォルダ名を生成
            new_folder_name = generate_password()

            # FOLDER_ID内に新しいフォルダを作成
            new_folder = client.folder(FOLDER_ID).create_subfolder(new_folder_name)
            print(f'Folder "{new_folder.name}" created with folder ID {new_folder.id}')

            # ファイルをアップロードする
            new_file = new_folder.upload(file_path)
            print('File "{0}" uploaded to Box with file ID {1}'.format(new_file.name, new_file.id))

            # アップロードしたファイルの共有リンクを作成（パスワードを含む）
            shared_link = new_file.get_shared_link(access='open')
            print(f'Shared link for the file with password protection: {shared_link}')

            # 一時ファイルを削除
            os.remove(file_path)
            
            #クライアント画面に表示する情報をリターン
            return render_template('result.html', shared_link=shared_link, new_folder_name=new_folder_name)
    return render_template('upload.html')

if __name__ == '__main__':
    app.run(debug=True)
