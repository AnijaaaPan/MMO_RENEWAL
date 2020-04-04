import json

# ./all_data/setting.jsonから保存しているtokenとprefixを取得します。
with open(r'./all_data/setting.json', encoding='utf-8') as fh:
    json_txt = fh.read()
    json_txt = str(json_txt).replace("'", '"').replace('True', 'true').replace('False', 'false')
    token = json.loads(json_txt)['token']
    prefix = json.loads(json_txt)['prefix']

# アイテムは辞書型で保存されています。自分が新しいアイテムを作る場合はここの中に作ってください。
# テスターの証という奴を追加してみたい場合は下のように追加してください。
item_lists = {
    -10: "運営の証",
    -9: "サポーターの証",
    # -8: "テスターの証",
    1: "エリクサー",
    2: "ファイアボールの書",
    3: "祈りの書"
}

# リニューアルコードをテストしているため分かりやすく兄じゃぁぁぁ # 3454のIDを記載しています。(私はTAOしか管理しないので残してもらっても消していただいてもかまいません)
# 運営コマンドを使用したい場合は使いたい垢のIDをこの中に入れると使用可能になり運営のみしかコマンドを打てないときにもテスターとしてコマンドを実行できるようになります。
admin_list = [304932786286886912] # admin_list = [304932786286886912, 304932786286886912](複数人の場合)
