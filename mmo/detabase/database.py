 # -*- coding: utf-8 -*-

import random
import math
import glob
import json
import traceback
import asyncio

from discord import Embed, NotFound, Forbidden
from all_data.all_data import item_lists

special_monster, N_monster = {}, {}
rera_monster, nomal_monster = [], []

f"""登録されているモンスターは起動時のみしか読み込まないので敵を追加する場合は再起動してください。f"""
for file in glob.glob("./monster/*"): # monsterディレクトリとかファイル一覧を取得
    with open(r'' + file + '', encoding='utf-8') as fh:
        json_txt = str(fh.read()).replace("'", '"').replace('True', 'true').replace('False', 'false')
        for x in json.loads(json_txt):
              # こういう分け方もあるよ！TAOではこっちにしてるけど分かりやすいと思って下のようにファイルごとにレアリティ決めちゃう感じにしてる
              # if "【レア】" == x["rank"]: # 敵のランクが【レア】だった場合
              #    rera_monster.append(x) # レア枠としてモンスターを登録
              # if "【通常】" == x["rank"]: # 敵のランクが【通常】だった場合
              #    nomal_monster.append(x) # 通常枠としてモンスターを登録

            if "rera" in f"{file}": # ファイル名に"rera"が入ってた場合
                rera_monster.append(x) # レア枠としてモンスターを登録
            if "normal" in f"{file}": # ファイル名に"normal"が入ってた場合
                nomal_monster.append(x) # 通常枠としてモンスターを登録

def monster_info(channel_id): # モンスターの名前、画像、ランクを取得
    if channel_id in special_monster: # 辞書であるspecial_monsterにチャンネルIDが存在していた場合
        monster_name = special_monster[channel_id]["name"] # モンスターの名前を取得
        monster_image = special_monster[channel_id]["img"] # モンスターの画像を取得
        monster_rank = special_monster[channel_id]["rank"] # モンスターのランクを取得
    else: # そうではない場合
        monsters = random.choice(nomal_monster) # 通常の敵をランダムで取得
        N_monster[channel_id] = monsters
        monster_name = monsters["name"] # モンスターの名前を取得
        monster_image = monsters["img"] # モンスターの画像を取得
        monster_rank = monsters["rank"] # モンスターのランクを取得
    return monster_name, monster_image, monster_rank

def monster_delete(channel_id): # そのチャンネルに存在してる敵の情報を全て削除
    if channel_id in N_monster: # 辞書であるN_monsterにチャンネルIDが存在していた場合
        del N_monster[channel_id] # N_monsterからチャンネルIDを削除
    if channel_id in special_monster: # 辞書であるspecial_monsterにチャンネルIDが存在していた場合
        del special_monster[channel_id] # special_monsterからチャンネルIDを削除

class Database:
    async def _attack(self, ctx, user_id, channel_id, conn, cur, bot): # 攻撃したときの関連の関数。
        try: # ERRORが起きるか起きないか。起きたらexceptに飛ばされる
            player_hp, error_message = await into_battle(ctx, user_id, channel_id, conn, cur, bot) # 攻撃したチャンネルでの戦闘状況を返す。
            if error_message: # 死んでた場合はerror_messageが返ってくる。　戦闘してるチャンネルと別の場所で攻撃してもerror_messageが返ってくる
                return await ctx.send(error_message)

            player_level = await get_player_level(ctx, user_id, conn, cur) # プレイヤーのレベルを取得
            boss_level, boss_hp = await get_boss_level_and_hp(ctx.guild.id, channel_id, conn, cur) # チャンネルの敵のレベルと現在の体力を返す

            rand = random.random() # 　乱数生成
            player_attack = get_player_attack(player_level, boss_level, rand) # 自分の攻撃ダメージを返す
            boss_hp -= player_attack # 敵の体力から自分の攻撃ダメージを引いて現在の敵の体力の計算
            monster_name, monster_image, monster_rank = monster_info(channel_id) # 敵の名前、画像、ランクを返す
            attack_message = get_attack_message(user_id, player_attack, monster_name, rand) # 自分から敵に対しての攻撃メッセージの生成

            if boss_hp <= 0: # 敵の残り体力が0未満になった場合 違う場合はelseに...
                win_message = await win_process(ctx, channel_id, boss_level, monster_name, conn, cur) # 経験値やアイテムなどの処理を行う
                await ctx.send(f"{attack_message}\n{win_message}" if len(f"{attack_message}\n{win_message}") <= 2000 else "2000文字対策用メッセージ")
                monster_delete(channel_id)
                return await Database().reset_battle(ctx, channel_id, conn, cur, level_up=True) # level_upをTrueにしてるから敵の階層が上がるようになる(デフォルトはFalse)
            else:
                await cur.execute("UPDATE channel_status SET boss_hp=? WHERE channel_id=?", (boss_hp, channel_id)) # 攻撃された敵の体力から差し引いた分の体力をデータベースにて更新
                await conn.commit() # データベースを最新の情報にするために更新する。 絶対必須

                boss_attack = get_boss_attack(boss_level) # 敵からの攻撃ダメージを返す
                player_hp -= boss_attack # 自分の体力から敵の攻撃ダメージを引いて現在の自分の体力の計算
                if boss_attack == 0: # かわす処理
                    pass
                elif player_hp <= 0: # 要するに死んだ
                    await cur.execute("UPDATE in_battle SET player_hp=0 WHERE user_id=?", (user_id,)) # 自分の残り体力を0に更新
                else: # 生きてた
                    await cur.execute("UPDATE in_battle SET player_hp=? WHERE user_id=?", (player_hp, user_id)) # 自分の体力から差し引いた分の体力をデータベースにて更新
                await conn.commit() # データベースを最新の情報にするために更新する。 絶対必須
                boss_attack_message = boss_attack_process(user_id, player_hp, player_level, monster_name, boss_attack) # 敵から自分に対しての攻撃メッセージの生成
                return await ctx.send(f"{attack_message}\n - {monster_name}のHP:`{boss_hp}`/{boss_level * 10 + 50}\n\n{boss_attack_message}")

        except (NotFound, asyncio.TimeoutError, Forbidden): # 編集した際に文字が見つからなかった, wait_forの時間制限を超過した場合, メッセージに接続できなかった
            return
        except: # 上のERROR以外のERROR出た場合はtracebackで表示するようにしています。 上手くコマンドが反応しない場合はコンソールを見てね！
            return print("エラー情報\n" + traceback.format_exc())

    async def _item(self, ctx, user_id, channel_id, item_name, mentions, conn, cur, bot): # アイテム関連の関数。
        try: # ERRORが起きるか起きないか。起きたらexceptに飛ばされる
            if not item_name: # item_nameが空だった場合
              # アイテムを所持してるかの確認。アイテムはitem_idで登録してるので名前をall_dataファイルのitem_lists変数から引っ張ってきます。
                await cur.execute("select distinct item_id,count FROM item WHERE user_id=? ORDER BY item_id;", (user_id,))
                i_list = ''.join(f'{item_lists[i[0]]} : {i[1]}個\n' for i in await cur.fetchall())
                msgs = list(filter(lambda a: a != "", ["\n".join(i_list.split("\n")[i:i + 25]) for i in range(0, len(i_list), 25)])) # 今後アイテムが増えた場合に25個のデータ(重複なし)でページ分け

                embeds = [Embed(description=f"```{i if i else 'アイテムを所持していません。'}```").set_thumbnail(url=ctx.author.avatar_url_as()).set_author(name=f"{ctx.author}のステータス:") for i in msgs]
                msg = await ctx.send(content=f"```diff\n1ページ/{len(embeds)}ページ目を表示中\n見たいページを発言してください。\n30秒経ったら処理は止まります。\n0と発言したら強制的に処理は止まります。```", embed=embeds[0])
                while True: # 処理が終わる(return)まで無限ループ
                    try: # ERRORが起きるか起きないか。起きたらexceptに飛ばされる
                        msg_react = await bot.wait_for('message', check=lambda m: m.author == ctx.author and m.content.isdigit() and 0 <= int(m.content) <= len(embeds), timeout=30)
                      # await self.bot.wait_for('message')で返ってくるのは文字列型
                        if msg_react.content == "0":
                          # このcontentの中にはゼロ幅スペースが入っています。Noneでもいいのですが編集者はこっちの方が分かりやすいからこうしています。
                            return await msg.edit(content="‌")
                        await msg.edit(content=f"```diff\n{int(msg_react.content)}ページ/{len(embeds)}ページ目を表示中\n見たいページを発言してください。\n30秒経ったら処理は止まります。\n0と発言したら強制的に処理は止まります。```", embed=embeds[int(msg_react.content) - 1])
                    except asyncio.TimeoutError: # wait_forの時間制限を超過した場合
                      # このcontentの中にはゼロ幅スペースが入っています。Noneでもいいのですが編集者はこっちの方が分かりやすいからこうしています。
                        return await msg.edit(content="‌", embed=Embed(title=f"時間切れです..."))

            if item_name in ["e", "elixir", "エリクサー"]: # item_nameが["e", "elixir", "エリクサー"]の中のどれかだったら
                return await ctx.send(await elixir(user_id, channel_id, conn, cur))
            elif item_name in ["f", "fire", "ファイアボールの書"]: # item_nameが["f", "fire", "ファイアボールの書"]の中のどれかだったら
                return await Database().fireball(ctx, user_id, channel_id, conn, cur, bot)
            elif item_name in ["p", "pray", "祈りの書"]: # item_nameが["p", "pray", "祈りの書"]の中のどれかだったら
                return await ctx.send(await pray(ctx, user_id, channel_id, mentions, conn, cur, bot))
            else: # item_nameでアイテムが存在してなかった場合
                return await ctx.send(embed=Embed(title=f"！？", description="そのアイテムは存在しません。"))

        except (NotFound, asyncio.TimeoutError, Forbidden): # 編集した際に文字が見つからなかった, wait_forの時間制限を超過した場合, メッセージに接続できなかった
            return
        except: # 上のERROR以外のERROR出た場合はtracebackで表示するようにしています。 上手くコマンドが反応しない場合はコンソールを見てね！
            return print("エラー情報\n" + traceback.format_exc())

    async def fireball(self, ctx, user_id, channel_id, conn, cur, bot): # アイテムでファイアーボールの書を使用したときの関数
        try: # ERRORが起きるか起きないか。起きたらexceptに飛ばされる
            player_hp, error_message = await into_battle(ctx, user_id, channel_id, conn, cur, bot) # 攻撃したチャンネルでの戦闘状況を返す。
            if error_message: # 死んでた場合はerror_messageが返ってくる。　戦闘してるチャンネルと別の場所で攻撃してもerror_messageが返ってくる
                return await ctx.send(error_message)

            if not await consume_an_item(user_id, 2, conn, cur): # ファイアボールの書を持ってる場合は1個消費し持ってない場合は下の処理になる
                return await ctx.send(f"<@{user_id}>はファイアボールの書を持っていない！")

            player_level = await get_player_level(ctx, user_id, conn, cur) # プレイヤーのレベルを取得
            boss_level, boss_hp = await get_boss_level_and_hp(ctx.guild.id, channel_id, conn, cur) # チャンネルの敵のレベルと現在の体力を返す
            player_attack = int(player_level * (1 + random.random()) / 10) # 自分の攻撃ダメージを返す
            boss_hp -= player_attack # 敵の体力から自分の攻撃ダメージを引いて現在の敵の体力の計算
            monster_name, monster_image, monster_rank = monster_info(channel_id) # 敵の名前、画像、ランクを返す
            attack_message = f"ファイアボール！<@{user_id}>は{monster_name}に`{player_attack}`のダメージを与えた！"
            if boss_hp <= 0: # 敵の残り体力が0未満になった場合 違う場合はelseに...
                win_message = await win_process(ctx, channel_id, boss_level, monster_name, conn, cur) # 経験値やアイテムなどの処理を行う
                await ctx.send(f"{attack_message}\n{win_message}" if len(f"{attack_message}\n{win_message}") <= 2000 else "2000文字対策用メッセージ")
                monster_delete(channel_id)
                return await Database().reset_battle(ctx, channel_id, conn, cur, level_up=True) # level_upをTrueにしてるから敵の階層が上がるようになる(デフォルトはFalse)
            else:
                await cur.execute("UPDATE channel_status SET boss_hp=? WHERE channel_id=?", (boss_hp, channel_id)) # 攻撃された敵の体力から差し引いた分の体力をデータベースにて更新
                await conn.commit() # データベースを最新の情報にするために更新する。 絶対必須
                return await ctx.send(f"{attack_message}\n{monster_name}のHP:`{boss_hp}`/{boss_level * 10 + 50}")

        except (NotFound, asyncio.TimeoutError, Forbidden): # 編集した際に文字が見つからなかった, wait_forの時間制限を超過した場合, メッセージに接続できなかった
            return
        except: # 上のERROR以外のERROR出た場合はtracebackで表示するようにしています。 上手くコマンドが反応しない場合はコンソールを見てね！
            return print("エラー情報\n" + traceback.format_exc())

    async def reset_battle(self, ctx, channel_id, conn, cur, level_up=False): # 戦闘状況がリセットされ更新される関数
        try: # ERRORが起きるか起きないか。起きたらexceptに飛ばされる
            await cur.execute("DELETE FROM in_battle WHERE channel_id=?;", (channel_id,)) # そのチャンネルの戦闘状況をリセットする
            await conn.commit() # データベースを最新の情報にするために更新する。 絶対必須

            if channel_id in special_monster: # resetされた場合にレア敵を削除し通常モンスターに入れ替える処理
                del special_monster[channel_id]

            boss_level, boss_hp = await get_boss_level_and_hp(ctx.guild.id, channel_id, conn, cur) # チャンネルの敵のレベルと現在の体力を返す
            if level_up: # 敵を倒した
                await cur.execute("UPDATE channel_status SET boss_level=boss_level+1 WHERE channel_id=?;", (channel_id,)) # チャンネルの敵のレベルの情報を1上げる
                await conn.commit() # データベースを最新の情報にするために更新する。 絶対必須

              # 50階層ごとに超強敵 5階層ごとに強敵出したい場合はこうします。 その場合は[if random.random() <= 0.1:]を[elif random.random() <= 0.1:]にしてね
              # if boss_level % 50 == 0:
              #    monster = random.choice(supertuyoi_monster)
              #    SST_monster[channel_id] = monster
              # elif boss_level % 5 == 0:
              #    monster = random.choice(tuyoi_monster)
              #    ST_monster[channel_id] = monster

                if random.random() <= 0.1: # 10分の1でレアモンスターになる
                    monster = random.choice(rera_monster) # レア敵の中からランダムで敵を取得
                    special_monster[channel_id] = monster
                else: # 通常的わっしょいわっしょい
                    monster = random.choice(nomal_monster) # 通常敵の中からランダムで敵を取得
                    N_monster[channel_id] = monster
                boss_level += 1 # boss_levelを1上げる

            else: # resetコマンドを打った
                monster = random.choice(nomal_monster)
                N_monster[channel_id] = monster

            await cur.execute("UPDATE channel_status SET boss_hp=boss_level*10+50 WHERE channel_id=?;", (channel_id,)) # チャンネルの敵の体力を更新する
            await conn.commit() # データベースを最新の情報にするために更新する。 絶対必須
            return await ctx.send(embed=Embed(title=f"{monster['name']}が待ち構えている...！\nLv.{boss_level}  HP:{boss_level * 10 + 50}").set_image(url=f"{monster['img']}"))

        except (NotFound, asyncio.TimeoutError, Forbidden): # 編集した際に文字が見つからなかった, wait_forの時間制限を超過した場合, メッセージに接続できなかった
            return
        except: # 上のERROR以外のERROR出た場合はtracebackで表示するようにしています。 上手くコマンドが反応しない場合はコンソールを見てね！
            return print("エラー情報\n" + traceback.format_exc())

async def into_battle(ctx, user_id, channel_id, conn, cur, bot): # 現在の戦闘状況を返す関数
    try: # ERRORが起きるか起きないか。起きたらexceptに飛ばされる
        error_message = "" # デフォルト空白
        player_level = await get_player_level(ctx, user_id, conn, cur) # プレイヤーのレベルを取得
        await cur.execute("SELECT channel_id, player_hp FROM in_battle WHERE user_id=?", (user_id,)) # チャンネルで戦ってるか否か
        in_battle = await cur.fetchone() # データを1個のみ取得 [1個のみ取得の場合は『fetchone()』 全ての場合は『fetchall()』]
        if not in_battle: # お初さんいらっしゃい
            player_hp = player_level*5+50 # デフォルト体力は自分のレベルかける5してそこから50を足します。
            await cur.execute("INSERT INTO in_battle values(?,?,?)", (user_id, channel_id, player_hp)) # そのチャンネルに自分が参加したというデータの挿入
            await conn.commit() # データベースを最新の情報にするために更新する。 絶対必須
            return player_hp, error_message # error_messageは空白のままなので処理は通る

        in_battle_channel_id = int(in_battle[0]) # 1mmも意味の無いintに変換
        battle_channel = bot.get_channel(in_battle_channel_id) # チャンネルIDからチャンネルを取得
        if not battle_channel: # 　そのチャンネル存在しないか認識できないようだよ！BOTが入ってないのかも！
            player_hp = player_level*5+50 # デフォルト体力は自分のレベルかける5してそこから50を足します。
            await cur.execute("DELETE FROM in_battle WHERE channel_id=?", (in_battle_channel_id,)) # そのチャンネルの戦闘状況をリセットする
            await conn.commit() # データベースを最新の情報にするために更新する。 絶対必須
            await cur.execute("INSERT INTO in_battle values(?,?,?)", (user_id, channel_id, player_hp)) # そのチャンネルに自分が参加したというデータの挿入
            await conn.commit() # データベースを最新の情報にするために更新する。 絶対必須
            return player_hp, error_message # error_messageは空白のままなので処理は通る

        player_hp = in_battle[1]
        if in_battle_channel_id != channel_id: # 発言チャンネルIDと自分が参加してるチャンネルIDが違った場合
            battle_field = "{}の # {}".format(battle_channel.guild.name, battle_channel.name) # ギルド名の # チャンネル名が返ってくる(「ここでresetしてください」と言う事)
            error_message = f"<@{user_id}>は`{battle_field}`で既に戦闘中だ。" # この文字列を返す
        elif player_hp == 0: # 自分の体力が0の場合(要するに死んでいる場合)
            error_message = f"<@{user_id}>はもうやられている！（戦いをやり直すには「!!reset」だ）" # この文字列を返す
        return player_hp, error_message # 別チャンネルまたは死んでる場合以外は処理が通る
    except: # 上のERROR以外のERROR出た場合はtracebackで表示するようにしています。 上手くコマンドが反応しない場合はコンソールを見てね！
        return print("エラー情報\n" + traceback.format_exc())

def get_attack_message(user_id, player_attack, monster_name, rand): # 敵への攻撃メッセージ生成関数
    try: # ERRORが起きるか起きないか。起きたらexceptに飛ばされる
        if player_attack == 0: # プレイヤーから敵に与えたダメージが0だった場合
            return f"<@{user_id}>の攻撃！{monster_name}にかわされてしまった...！！" # この文字列を返す
        else: # 与ダメが0では無かった場合
            return f"<@{user_id}>の攻撃！{'会心の一撃！' if rand > 0.96 else ''}{monster_name}に`{player_attack}`のダメージを与えた！" # この文字列を返す
    except: # 上のERROR以外のERROR出た場合はtracebackで表示するようにしています。 上手くコマンドが反応しない場合はコンソールを見てね！
        return print("エラー情報\n" + traceback.format_exc())

async def win_process(ctx, channel_id, exp, monster_name, conn, cur): # 敵を倒して戦闘が終了したときの関数
    try: # ERRORが起きるか起きないか。起きたらexceptに飛ばされる
        level_up_comments, members = [], "" # 誰かがレベルアップしたとき用の空リスト, 経験値を取得したとき用の空のメッセージ
        fire_members, elixir_members, pray_members = "", "", "" # 誰かがアイテムをゲットしたとき用の空のメッセージ
        await cur.execute("SELECT user_id FROM in_battle WHERE channel_id=?", (channel_id,)) # 戦闘に参加したユーザーのリスト
        for member_id in [m[0] for m in await cur.fetchall()]:
            level_up_comments.append(await experiment(ctx, member_id, exp, conn, cur)) # レベルが上がったかどうかの判定 上がった場合はメッセージが返ってきて上がってない場合は空のメッセージが返ってくる
            members += "<@{}> ".format(member_id) # 経験値をゲットしたメンバーをメッセージに追加
          # 今回取得した経験値を2乗しそれに0.02をかけてその状態から自分の総合計経験値数を割る
          # 上記の状態と0.1のどっちの数字の方が少ないかを取得
            p = min((0.02*(exp**2)) / await get_player_exp(ctx, member_id, conn, cur), 0.1)
            if exp % 50 == 0 and random.random() < p: # 倒した敵のレベルが50の倍数だった場合かrandom.random()で生成した乱数よりpの確率の方が上だった場合
                elixir_members += "<@{}> ".format(member_id) # アイテムをゲットしたメンバーをメッセージに追加
                await obtain_an_item(conn, cur, member_id, 1) # 処理が通った運良き戦闘メンバーに『エリクサー』を1個付与
            if random.random() < p: # random.random()で生成した乱数よりpの確率の方が上だった場合
                fire_members += "<@{}> ".format(member_id) # アイテムをゲットしたメンバーをメッセージに追加
                await obtain_an_item(conn, cur, member_id, 2) # 処理が通った運良き戦闘メンバーに『ファイアーボールの書』を1個付与
            if random.random() < p * 2: # random.random()で生成した乱数よりpの確率の方が上だった場合
                pray_members += "<@{}> ".format(member_id) # アイテムをゲットしたメンバーをメッセージに追加
                await obtain_an_item(conn, cur, member_id, 3) # 処理が通った運良き戦闘メンバーに『祈りの書』を1個付与

        if fire_members: # 『ファイアボールの書』をゲットしたメンバーが居た場合[fire_members]の最後に下記のメッセージを追加
            fire_members += "は`ファイアボールの書`を手に入れた！"
        if elixir_members: # 『エリクサー』をゲットしたメンバーが居た場合[elixir_members]の最後に下記のメッセージを追加
            elixir_members += "は`エリクサー`を手に入れた！"
        if pray_members: # 『祈りの書』をゲットしたメンバーが居た場合[pray_members]の最後に下記のメッセージを追加
            pray_members += "は`祈りの書`を手に入れた！"

        level_up_comment = "\n".join([c for c in level_up_comments if c]) # レベルが上がったメッセージを改行して表示
        item_get = "\n".join(c for c in [elixir_members, fire_members, pray_members] if c) # アイテムごとにゲットしたメンバーのメッセージを改行して表示
        return f"{monster_name}を倒した！\n\n{members}は`{exp}`の経験値を得た。{level_up_comment}\n{item_get}" # この文字列を返す
    except: # 上のERROR以外のERROR出た場合はtracebackで表示するようにしています。 上手くコマンドが反応しない場合はコンソールを見てね！
        return print("エラー情報\n" + traceback.format_exc())

def boss_attack_process(user_id, player_hp, player_level, monster_name, boss_attack): # 敵からの攻撃メッセージ生成関数
    try: # ERRORが起きるか起きないか。起きたらexceptに飛ばされる
        if boss_attack == 0: # 敵からの攻撃が0ダメだった場合
            return f"{monster_name}の攻撃！<@{user_id}>は華麗にかわした！\n - <@{user_id}>のHP:`{player_hp}`/{player_level * 5 + 50}" # この文字列を返す
        elif player_hp <= 0: # 敵からのダメを受けて自分の体力が0未満になってしまった場合
            return f"{monster_name}の攻撃！<@{user_id}>は`{boss_attack}`のダメージを受けた。\n - <@{user_id}>のHP:`0`/{player_level * 5 + 50}\n<@{user_id}>はやられてしまった。。。" # この文字列を返す
        else: # 生き残った場合
            return f"{monster_name}の攻撃！<@{user_id}>は`{boss_attack}`のダメージを受けた。\n - <@{user_id}>のHP:`{player_hp}`/{player_level * 5 + 50}" # この文字列を返す
    except: # 上のERROR以外のERROR出た場合はtracebackで表示するようにしています。 上手くコマンドが反応しない場合はコンソールを見てね！
        return print("エラー情報\n" + traceback.format_exc())

def get_player_attack(player_level, boss_level, rand): # 敵へのダメ計算関数
    try: # ERRORが起きるか起きないか。起きたらexceptに飛ばされる
        if rand < 0.01: # 100分の1で攻撃力が0になる^^
            return 0 # この整数を返す
        elif boss_level % 50 == 0: # 敵の階層の倍数が50だった場合
            return int(player_level*(rand/2+1.5 if rand<0.96 else 3) + 10) # この整数を返す ※会心(randが0.96より大きい場合)だった場合は3を返す
        elif boss_level % 5 == 0: # 敵の階層の倍数が5だった場合
            return int(player_level*(rand/2+0.8 if rand<0.96 else 3) + 10) # この整数を返す ※会心(randが0.96より大きい場合)だった場合は3を返す
        else: # 特に何でもなかった場合
            return int(player_level*(rand/2+1 if rand<0.96 else 3) + 10) # この整数を返す ※会心(randが0.96より大きい場合)だった場合は3を返す

    except: # 上のERROR以外のERROR出た場合はtracebackで表示するようにしています。 上手くコマンドが反応しない場合はコンソールを見てね！
        return print("エラー情報\n" + traceback.format_exc())

def get_boss_attack(boss_level): # 敵からのダメ計算関数
    try: # ERRORが起きるか起きないか。起きたらexceptに飛ばされる
        if random.random() < 0.01: # 100分の1で受けるダメージが0になる^^
            return 0 # この整数を返す
        elif boss_level % 50 == 0:
            return int(boss_level * (1 + random.random()) * 5) # この整数を返す
        elif boss_level % 5 == 0:
            return int(boss_level * (1 + random.random()) * 3) # この整数を返す
        else:
            return int(boss_level * (2 + random.random()) + 5) # この整数を返す
    except: # 上のERROR以外のERROR出た場合はtracebackで表示するようにしています。 上手くコマンドが反応しない場合はコンソールを見てね！
        return print("エラー情報\n" + traceback.format_exc())

async def elixir(user_id, channel_id, conn, cur): # アイテムのエリクサーを使用した場合の関数
    try: # ERRORが起きるか起きないか。起きたらexceptに飛ばされる
        if not await consume_an_item(user_id, 1, conn, cur): # エリクサーを持ってる場合は1個消費し持ってない場合は下の処理になる
            return f"<@{user_id}>はエリクサーを持っていない！" # この文字列を返す

       # 参加してるユーザのレベルを取得しそこからそのユーザーの全体力を計算
        await cur.execute("SELECT player.user_id, player.exp FROM in_battle, player WHERE in_battle.channel_id=? AND player.user_id=in_battle.user_id", (channel_id,))
        for in_battle in await cur.fetchall():
            full_hp = int(math.sqrt(in_battle[1]))*5+50
            await cur.execute("UPDATE in_battle SET player_hp=? WHERE user_id=?", (full_hp, in_battle[0])) # チャンネルに参加してるユーザーの体力を全回復
            await conn.commit() # データベースを最新の情報にするために更新する。 絶対必須
        return f"<@{user_id}>はエリクサーを使った！このチャンネルの仲間全員が全回復した！" # この文字列を返す
    except: # 上のERROR以外のERROR出た場合はtracebackで表示するようにしています。 上手くコマンドが反応しない場合はコンソールを見てね！
        return print("エラー情報\n" + traceback.format_exc())

async def pray(ctx, user_id, channel_id, mentions, conn, cur, bot): # アイテムの祈りの書を使用した場合の関数
    try: # ERRORが起きるか起きないか。起きたらexceptに飛ばされる
        if not mentions: # ユーザーに対してのメンションがない場合
            return "祈りの書は仲間を復活させます。祈る相手を指定して使います。\n例)!!item 祈りの書 @ユーザー名" # この文字列を返す

        prayed_user_id = mentions[0].id # メンションの中のidを取得
        await cur.execute("SELECT player_hp FROM in_battle WHERE channel_id=? and user_id=?", (channel_id, prayed_user_id)) # 　指定したユーザーの体力を取得
        prayed_user = await cur.fetchone() # データを1個のみ取得 [1個のみ取得の場合は『fetchone()』 全ての場合は『fetchall()』]
        if not prayed_user: # 指定したユーザーが戦闘に参加してない場合
            return f"<@{prayed_user_id}>は戦闘に参加していない！" # この文字列を返す
        if prayed_user[0] != 0: # 指定したユーザーの体力が0では無かった場合(死んでなかった場合)
            return f"<@{prayed_user_id}>はまだ生きている！" # この文字列を返す
        if not await consume_an_item(user_id, 3, conn, cur): # 祈りの書を持ってる場合は1個消費し持ってない場合は下の処理になる
            return f"<@{user_id}>は祈りの書を持っていない！" # この文字列を返す

        player_hp, error_message = await into_battle(ctx, user_id, channel_id, conn, cur, bot) # 攻撃したチャンネルでの戦闘状況を返す。
        if error_message: # 死んでた場合はerror_messageが返ってくる。　戦闘してるチャンネルと別の場所で攻撃してもerror_messageが返ってくる
            return error_message # この文字列を返す

        await cur.execute("UPDATE in_battle SET player_hp=1 WHERE user_id=?", (prayed_user_id,)) # 指定したユーザーの体力を1にする！復活！
        await conn.commit() # データベースを最新の情報にするために更新する。 絶対必須
        return f"<@{user_id}>は祈りを捧げ、<@{prayed_user_id}>は復活した！\n<@{prayed_user_id}> 残りHP: 1" # この文字列を返す
    except: # 上のERROR以外のERROR出た場合はtracebackで表示するようにしています。 上手くコマンドが反応しない場合はコンソールを見てね！
        return print("エラー情報\n" + traceback.format_exc())

async def get_player_exp(ctx, user_id, conn, cur): # ユーザーの総経験値を返す関数
    try: # ERRORが起きるか起きないか。起きたらexceptに飛ばされる
        await cur.execute("SELECT exp FROM player WHERE user_id=?", (user_id,)) # ユーザーの経験を取得
        player = await cur.fetchone() # データを1個のみ取得 [1個のみ取得の場合は『fetchone()』 全ての場合は『fetchall()』]
        if not player: # ユーザーのデータが存在してない場合
            await cur.execute("INSERT INTO player values(?,?,?)", (user_id, 1, 1 if ctx.author.bot else 0)) # ユーザーのデータを新たに追加 ボットの場合は1、ユーザーの場合は0を挿入
            await conn.commit() # データベースを最新の情報にするために更新する。 絶対必須
            return 1 # この整数を返す
        return player[0] # この整数を返す
    except: # 上のERROR以外のERROR出た場合はtracebackで表示するようにしています。 上手くコマンドが反応しない場合はコンソールを見てね！
        return print("エラー情報\n" + traceback.format_exc())

async def get_player_level(ctx, user_id, conn, cur): # ユーザーのレベルを返す関数
    try: # ERRORが起きるか起きないか。起きたらexceptに飛ばされる
        await cur.execute("SELECT exp FROM player WHERE user_id=?", (user_id,)) # ユーザーの経験を取得
        player = await cur.fetchone() # データを1個のみ取得 [1個のみ取得の場合は『fetchone()』 全ての場合は『fetchall()』]
        if not player: # ユーザーのデータが存在してない場合
            await cur.execute("INSERT INTO player values(?,?,?)", (user_id, 1, 1 if ctx.author.bot else 0)) # ユーザーのデータを新たに追加 [ユーザーID,経験値,ボットの場合は1、ユーザーの場合は0を挿入]
            await conn.commit() # データベースを最新の情報にするために更新する。 絶対必須
            return 1 # この整数を返す
        return int(math.sqrt(player[0])) # この整数を返す
    except: # 上のERROR以外のERROR出た場合はtracebackで表示するようにしています。 上手くコマンドが反応しない場合はコンソールを見てね！
        return print("エラー情報\n" + traceback.format_exc())

async def get_boss_level_and_hp(server_id, channel_id, conn, cur): # チャンネルの敵のレベルと現在の体力を返す処理
    try: # ERRORが起きるか起きないか。起きたらexceptに飛ばされる
        await cur.execute("SELECT boss_level, boss_hp FROM channel_status WHERE channel_id=?", (channel_id,)) # チャンネルの敵のレベルと敵の体力を返す
        channel_status = await cur.fetchone() # データを1個のみ取得 [1個のみ取得の場合は『fetchone()』 全ての場合は『fetchall()』]
        if not channel_status: # チャンネルのデータが存在してない場合
            await cur.execute("INSERT INTO channel_status values(?, ?, ?, ?)", (server_id, channel_id, 1, 50)) # チャンネルのデータを新たに追加 [サーバーID, チャンネルID, レベル, 体力]
            await conn.commit() # データベースを最新の情報にするために更新する。 絶対必須
            return 1, 50 # この整数を返す
        return int(channel_status[0]), int(channel_status[1]) # この整数を返す
    except: # 上のERROR以外のERROR出た場合はtracebackで表示するようにしています。 上手くコマンドが反応しない場合はコンソールを見てね！
        return print("エラー情報\n" + traceback.format_exc())

async def experiment(ctx, user_id, exp, conn, cur): # 経験値を足す関数
    try: # ERRORが起きるか起きないか。起きたらexceptに飛ばされる
        player_exp = await get_player_exp(ctx, user_id, conn, cur) # ユーザーの経験値を取得
        next_exp = player_exp + exp # 現在の経験値と今回取得した経験値を足す
        current_level = int(math.sqrt(player_exp)) # 経験値を足す前のレベル
        await cur.execute("UPDATE player SET exp=? WHERE user_id=?", (next_exp, user_id)) # 現在の経験値と今回取得した経験値にデータを更新する
        await conn.commit() # データベースを最新の情報にするために更新する。 絶対必須
        if next_exp > (current_level + 1) ** 2: # 更新後の経験値が自分のレベル+1の2乗より多かった場合
            return f"<@{user_id}>はレベルアップした！`Lv.{current_level} -> Lv.{int(math.sqrt(next_exp))}`" # この文字列を返す
        return "" # この文字列を返す
    except: # 上のERROR以外のERROR出た場合はtracebackで表示するようにしています。 上手くコマンドが反応しない場合はコンソールを見てね！
        return print("エラー情報\n" + traceback.format_exc())

async def obtain_an_item(conn, cur, user_id, item_id):
    try: # ERRORが起きるか起きないか。起きたらexceptに飛ばされる
        await cur.execute("SELECT * FROM item WHERE user_id=? and item_id=?", (user_id, item_id)) # ユーザーIDとアイテムIDを
        count = await cur.fetchone() # データを1個のみ取得 [1個のみ取得の場合は『fetchone()』 全ての場合は『fetchall()』]
        if count: # アイテムが存在するか否か
            await cur.execute("UPDATE item SET count=count+1 WHERE user_id=? and item_id=?", (user_id, item_id)) # 指定したアイテムIDのアイテムの数を1増やす
        else: # 存在してなかった
            await cur.execute("INSERT INTO item VALUES(?,?,1)", (user_id, item_id)) # アイテムをデータに追加 [ユーザーID, アイテムID, 個数]
        await conn.commit() # データベースを最新の情報にするために更新する。 絶対必須
        return
    except: # 上のERROR以外のERROR出た場合はtracebackで表示するようにしています。 上手くコマンドが反応しない場合はコンソールを見てね！
        return print("エラー情報\n" + traceback.format_exc())

async def consume_an_item(user_id, item_id, conn, cur):
    try: # ERRORが起きるか起きないか。起きたらexceptに飛ばされる
        await cur.execute("SELECT count FROM item WHERE user_id=? and item_id=?", (user_id, item_id))
        current_count = await cur.fetchone() # データを1個のみ取得 [1個のみ取得の場合は『fetchone()』 全ての場合は『fetchall()』]
        if not current_count: # 存在してなかった
            return False
        if current_count[0] <= 1: # 残りのアイテムの数が0になって場合
            await cur.execute("DELETE FROM item WHERE user_id=? and item_id=?", (user_id, item_id)) # アイテムが存在するか否か
        else: # 存在してなかった
            await cur.execute("UPDATE item SET count=count-1 WHERE user_id=? and item_id=?", (user_id, item_id)) # アイテムの数を1個減らす
        await conn.commit() # データベースを最新の情報にするために更新する。 絶対必須
        return True
    except: # 上のERROR以外のERROR出た場合はtracebackで表示するようにしています。 上手くコマンドが反応しない場合はコンソールを見てね！
        return print("エラー情報\n" + traceback.format_exc())
