 # -*- coding: utf-8 -*-

import math
import random
import json
import traceback
import asyncio

from discord.ext import commands
from .detabase import database
from discord import Embed, NotFound, Forbidden
from all_data.all_data import item_lists, admin_list, prefix

f = open(r'./all_data/training.json', encoding='utf-8')
training_set = json.load(f)

def split_len(s: str, len_i: int) -> list:
    _ = s.split("\n")
    i = 1
    if len(_) <= 1:
        return _
    while i < len(_):
        if len(f"{_[i - 1]}\n{_[i]}") < len_i:
            _[i - 1] += "\n" + _.pop(i)
            continue
        i += 1
    return _

class command(commands.Cog): #ここのcommandはhelpの時に[{prefix}help コマンド名]としたときにこのファイルのコマンドが指定されたときにクラス名を取得するので変える場合はhelpの中も変えてください。
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="help", pass_context=True, description='ユーザーコマンド') # コマンド名:『help』 省略コマンド:『なし』
    @commands.bot_has_permissions(read_messages=True, send_messages=True, embed_links=True, add_reactions=True, manage_messages=True, read_message_history=True) #これ絶対消しちゃダメ
    async def helps(self, ctx, command_content=""): #既に存在する関数名だったらERROR出るのでもし今後コマンドを追加するならコマンド名と同じ関数名にして下さい。(ここは例外)
        f"""
        {prefix}helpでコマンドの処理を開始。 ヘルプを表示します。
        ボットの運営の場合は新たなページが表示されます。
        『@commands.command(name="コマンド名", description='この場所')』
        {prefix}help コマンド名で上記の『この場所』という部分が表示されるよ！
        今後新たにhelp_messageに文字列を追加した場合に備えてページ分けを自動でさせてます。
        f"""
        try: # ERRORが起きるか起きないか。起きたらexceptに飛ばされる
          # sqlite_listの中からデータベースに接続したというオブジェクトを取得
            _, conn, cur = [sql for sql in self.bot.sqlite_list if ctx.author.id == sql[0]][0]
            if command_content == "":
                help_message = [
                    f"```{prefix}help | このメッセージの表示をします\n{prefix}attack/atk | チャンネル上のモンスターに攻撃します\n{prefix}item/i アイテム名/アイテム名の頭文字(e,f,i)) |\n選択したアイテムを使用します [例 {prefix}i f]\n{prefix}status/st | 自分のステータスを表示します\n{prefix}reset/rs/re | バトルをやり直します\n{prefix}t | 4字熟語クイズトレーニングをします```",
                    f"```{prefix}ranking | 鯖ランキングをまとめました。```"
                ]
                if ctx.author.id in admin_list: # BOT運営の人は新たなページが見れるようになります。
                    help_message.append(f"```{prefix}eval | 何でもできる。最高コマンド。\n{prefix}all | 全データを削除する\n{prefix}db | データベースに接続する\n{prefix}zukan | 現在登録されてる敵の図鑑一覧\n{prefix}exp | 指定したユーザーに対して経験値の付与\n{prefix}ban | 指定したユーザーをBANする\n{prefix}unban | 指定したユーザーのBANを解除する\n{prefix}database | データベースの再生成や全削除")

                embeds = []
                for embed in help_message:
                    embeds.append(Embed(title=f"TAO(Tsukishima Art Online)の遊び方", description=embed).set_thumbnail(url=self.bot.user.avatar_url_as()).set_footer(text="[{prefix}help コマンド名]で詳細を開けるよ"))
                msg = await ctx.send(content=f"```diff\n1ページ/{len(embeds)}ページ目を表示中\n見たいページを発言してください。\n30秒経ったら処理は止まります。\n0と発言したら強制的に処理は止まります。```", embed=embeds[0])
                while True: # 処理が終わる(return)まで無限ループ
                    try: # ERRORが起きるか起きないか。起きたらexceptに飛ばされる
                        msg_react = await self.bot.wait_for('message', check=lambda m: m.author == ctx.author and m.content.isdigit() and 0 <= int(m.content) <= len(embeds), timeout=30)
                        # await self.bot.wait_for('message')で返ってくるのは文字列型
                        if msg_react.content == "0":
                            # このcontentの中にはゼロ幅スペースが入っています。Noneでもいいのですが編集者はこっちの方が分かりやすいからこうしています。
                            return await msg.edit(content="‌")
                        await msg.edit(content=f"```diff\n{int(msg_react.content)}ページ/{len(embeds)}ページ目を表示中\n見たいページを発言してください。\n30秒経ったら処理は止まります。\n0と発言したら強制的に処理は止まります。```", embed=embeds[int(msg_react.content)-1])
                    except asyncio.TimeoutError: # wait_forの時間制限を超過した場合
                        # このcontentの中にはゼロ幅スペースが入っています。Noneでもいいのですが編集者はこっちの方が分かりやすいからこうしています。
                        return await msg.edit(content="‌", embed=Embed(title=f"時間切れです..."))

            else:
                for extension in ["command", "debug"]:
                    for c in self.bot.get_cog(extension).get_commands(): # 編集した際に文字が見つからなかった, wait_forの時間制限を超過した場合, メッセージに接続できなかった
                        if command_content in [c.name] + c.aliases: # aliasesはリストで返ってくるので[c.name]で雑対応
                            embeds = Embed(title=f"コマンド名:『{prefix}{command_content}』", description=f"説明:```{c.description}```") # コマンド名とその説明(description)の取得
                            embeds.set_thumbnail(url=self.bot.user.avatar_url_as()) # BOTのアイコンの表示
                            embeds.set_footer(text="その他の同じコマンド: " + ",".join([c.name] + c.aliases)) # aliasesが設定されてる場合はここに表示されます。
                            return await ctx.send(embed=embeds)

                return await ctx.send(embed=Embed(title=f"コマンド名:『{prefix}{command_content}』", description=f"説明:```おっと、このコマンドは存在しないようだ！\n君が運営になってこのコマンドを追加してみないか？```"))

        except (NotFound, asyncio.TimeoutError, Forbidden): # 編集した際に文字が見つからなかった, wait_forの時間制限を超過した場合, メッセージに接続できなかった
            return
        except: # 上のERROR以外のERROR出た場合はtracebackで表示するようにしています。 上手くコマンドが反応しない場合はコンソールを見てね！
            return print("エラー情報\n" + traceback.format_exc())

    @commands.command(name="attack", aliases=["atk"], pass_context=True, description='ユーザーコマンド') # コマンド名:『attack』 省略コマンド:『atk』
    @commands.bot_has_permissions(read_messages=True, send_messages=True, embed_links=True, add_reactions=True, manage_messages=True, read_message_history=True) #これ絶対消しちゃダメ
    async def attack(self, ctx): #既に存在する関数名だったらERROR出るのでもし今後コマンドを追加するならコマンド名と同じ関数名にして下さい。
        f"""敵に攻撃するf"""
        try: # ERRORが起きるか起きないか。起きたらexceptに飛ばされる
          # sqlite_listの中からデータベースに接続したというオブジェクトを取得
            _, conn, cur = [sql for sql in self.bot.sqlite_list if ctx.author.id == sql[0]][0]
            await database.Database()._attack(ctx, ctx.author.id, ctx.channel.id, conn, cur, self.bot)
            return await conn.commit()

        except (NotFound, asyncio.TimeoutError, Forbidden): # 編集した際に文字が見つからなかった, wait_forの時間制限を超過した場合, メッセージに接続できなかった
            return
        except: # 上のERROR以外のERROR出た場合はtracebackで表示するようにしています。 上手くコマンドが反応しない場合はコンソールを見てね！
            return print("エラー情報\n" + traceback.format_exc())

    @commands.command(name="item", aliases=["i"], pass_context=True, description='ユーザーコマンド') # コマンド名:『item』 省略コマンド:『i』
    @commands.bot_has_permissions(read_messages=True, send_messages=True, embed_links=True, add_reactions=True, manage_messages=True, read_message_history=True) #これ絶対消しちゃダメ
    async def item(self, ctx, item_name=""): #既に存在する関数名だったらERROR出るのでもし今後コマンドを追加するならコマンド名と同じ関数名にして下さい。
        f"""
        アイテムを使う
        item_nameが何もないの場合は手持ちアイテムのリストが返ってくるよ！
        f"""
        try: # ERRORが起きるか起きないか。起きたらexceptに飛ばされる
          # sqlite_listの中からデータベースに接続したというオブジェクトを取得
            _, conn, cur = [sql for sql in self.bot.sqlite_list if ctx.author.id == sql[0]][0]
            await database.Database()._item(ctx, ctx.author.id, ctx.channel.id, item_name, ctx.message.mentions, conn, cur, self.bot)
            return await conn.commit()

        except (NotFound, asyncio.TimeoutError, Forbidden): # 編集した際に文字が見つからなかった, wait_forの時間制限を超過した場合, メッセージに接続できなかった
            return
        except: # 上のERROR以外のERROR出た場合はtracebackで表示するようにしています。 上手くコマンドが反応しない場合はコンソールを見てね！
            return print("エラー情報\n" + traceback.format_exc())

    @commands.command(name='status', aliases=['st'], pass_context=True, description="ユーザーコマンド") # コマンド名:『status』 省略コマンド:『st』
    @commands.bot_has_permissions(read_messages=True, send_messages=True, embed_links=True, add_reactions=True, manage_messages=True, read_message_history=True) #これ絶対消しちゃダメ
    async def status(self, ctx): #既に存在する関数名だったらERROR出るのでもし今後コマンドを追加するならコマンド名と同じ関数名にして下さい。
        f"""
        ステータスの表示。
        今後アイテム追加した場合に備えてページ分けを自動でさせてます。
        f"""
        try: # ERRORが起きるか起きないか。起きたらexceptに飛ばされる
          # sqlite_listの中からデータベースに接続したというオブジェクトを取得
            _, conn, cur = [sql for sql in self.bot.sqlite_list if ctx.author.id == sql[0]][0]
            user = ctx.author
            user_id = ctx.author.id
            user_name = ctx.author.nick if ctx.author.nick else ctx.author.name

          # ユーザーの総経験値を取得
            player_exp = await database.get_player_exp(ctx, user_id, conn, cur)

          # 戦闘チャンネルの確認
            await cur.execute("select distinct channel_id FROM in_battle WHERE user_id=?", (user_id,))
            in_battle = await cur.fetchone()
            battle_str = f"{self.bot.get_channel(in_battle[0]).guild.name}の{self.bot.get_channel(in_battle[0]).mention}" if in_battle and self.bot.get_channel(in_battle[0]) else "現在休戦中or認識出来ないチャンネル"

          # アイテムを所持してるかの確認。アイテムはitem_idで登録してるので名前をall_dataファイルのitem_lists変数から引っ張ってきます。
            await cur.execute("select distinct item_id,count FROM item WHERE user_id=? ORDER BY item_id;", (user_id,))
            i_list = ''.join(f'{item_lists[i[0]]} : {i[1]}個\n' for i in await cur.fetchall())
          # 今後アイテムが増えた場合に25個のデータ(重複なし)でページ分け
            msgs = list(filter(lambda a: a != "", ["\n".join(i_list.split("\n")[i:i + 25]) for i in range(0, len(i_list), 25)] if i_list != "" else ["無し"]))

          # 現在のユーザのランキングlistで返しindexで順位を取得する方法にしています。
            await cur.execute("select distinct user_id FROM player ORDER BY exp DESC;")
            user_rank = [r[0] for r in await cur.fetchall()]

          # 経験値をmath.sqrt(平方根の計算)を使用し求めます。整数を返すためにint()を使用しています。
            player_level = int(math.sqrt(player_exp))
            embeds = []
            embed = Embed()
            embed.add_field(name="Lv", value=str(player_level))
            embed.add_field(name="HP", value=str(player_level*5+50))
            embed.add_field(name="ATK", value=str(int(player_level*5+50)))
            embed.add_field(name="EXP", value=str(player_exp))
          # レベル+1の必要経験値数(2乗)-現在の経験値数で計算しています。
            embed.add_field(name="次のLvまで", value=str((player_level+1)**2-player_exp)+"exp")
            embed.add_field(name="戦闘状況:", value=battle_str)
            embed.add_field(name="順位:", value=f"{user_rank.index(user_id) + 1}位")
          # ユーザーのアイコン表示
            embed.set_thumbnail(url=user.avatar_url_as())
            embed.set_author(name=f"{user_name}のステータス:")
            embeds.append(embed)

            [embeds.append(Embed(description=f"```{i if i else 'アイテムを所持していません。'}```").set_thumbnail(url=user.avatar_url_as()).set_author(name=f"{user_name}のステータス:")) for i in msgs]

            msg = await ctx.send(content=f"```diff\n1ページ/{len(embeds)}ページ目を表示中\n見たいページを発言してください。\n30秒経ったら処理は止まります。\n0と発言したら強制的に処理は止まります。```", embed=embeds[0])
            while True: # 処理が終わる(return)まで無限ループ
                try: # ERRORが起きるか起きないか。起きたらexceptに飛ばされる
                    msg_react = await self.bot.wait_for('message', check=lambda m: m.author == ctx.author and m.content.isdigit() and 0 <= int(m.content) <= len(embeds), timeout=30)
                  # await self.bot.wait_for('message')で返ってくるのは文字列型
                    if msg_react.content == "0":
                      # このcontentの中にはゼロ幅スペースが入っています。Noneでもいいのですが編集者はこっちの方が分かりやすいからこうしています。
                        return await msg.edit(content="‌")
                    await msg.edit(content=f"```diff\n{int(msg_react.content)}ページ/{len(embeds)}ページ目を表示中\n見たいページを発言してください。\n30秒経ったら処理は止まります。\n0と発言したら強制的に処理は止まります。```", embed=embeds[int(msg_react.content)-1])
                except asyncio.TimeoutError: # wait_forの時間制限を超過した場合
                  # このcontentの中にはゼロ幅スペースが入っています。Noneでもいいのですが編集者はこっちの方が分かりやすいからこうしています。
                    return await msg.edit(content="‌", embed=Embed(title=f"時間切れです..."))

        except (NotFound, asyncio.TimeoutError, Forbidden): # 編集した際に文字が見つからなかった, wait_forの時間制限を超過した場合, メッセージに接続できなかった
            return
        except: # 上のERROR以外のERROR出た場合はtracebackで表示するようにしています。 上手くコマンドが反応しない場合はコンソールを見てね！
            return print("エラー情報\n" + traceback.format_exc())

    @commands.command(name='inquiry', aliases=['inq'], pass_context=True, description="ユーザーコマンド") # コマンド名:『inquiry』 省略コマンド:『inq』
    @commands.bot_has_permissions(read_messages=True, send_messages=True, embed_links=True, add_reactions=True, manage_messages=True, read_message_history=True) #これ絶対消しちゃダメ
    async def inquiry(self, ctx): #既に存在する関数名だったらERROR出るのでもし今後コマンドを追加するならコマンド名と同じ関数名にして下さい。
        f"""
        今何人が戦闘に参加しているのかを表示。
        1500文字毎にページを分けさせるようにしてます。
        戦闘が行われない場合は行われてないというメッセージが返ってきます。
        f"""
        try: # ERRORが起きるか起きないか。起きたらexceptに飛ばされる
          # sqlite_listの中からデータベースに接続したというオブジェクトを取得
            _, conn, cur = [sql for sql in self.bot.sqlite_list if ctx.author.id == sql[0]][0]
          # 戦闘が行われてるかの確認
            await cur.execute("SELECT * FROM in_battle WHERE channel_id=?", (ctx.channel.id,))
            in_battle = await cur.fetchone()
            if in_battle:
              # 現在戦ってる敵のレベルとHPを持ってくる
                b_l, _ = await database.get_boss_level_and_hp(ctx.guild.id, ctx.channel.id, conn, cur)
              # そのチャンネルの敵の情報を引き出す。
                b_n, b_i,= database.monster_info(ctx.channel.id)

              # 現在散会してるユーザー全員を取得し1500文字でページ分け
                await cur.execute("select distinct * from in_battle where channel_id=?;", (ctx.channel.id,))
                in_battle = split_len("\n".join([f"- <@{i[0]}> | 残りHP: {i[2]}" for i in await cur.fetchall()]), 1500)

                embeds = []
                for embed in in_battle:
                    embeds.append(Embed(title=f"Lv:{b_l}の{b_n}と戦闘中だ！").set_thumbnail(url=b_i).add_field(name="戦闘中のメンバー", value=embed, inline=False).set_author(name=f"このチャンネルの戦闘状況"))

                msg = await ctx.send(content=f"```diff\n1ページ/{len(embeds)}ページ目を表示中\n見たいページを発言してください。\n30秒経ったら処理は止まります。\n0と発言したら強制的に処理は止まります。```", embed=embeds[0])
                while True: # 処理が終わる(return)まで無限ループ
                    try: # ERRORが起きるか起きないか。起きたらexceptに飛ばされる
                        msg_react = await self.bot.wait_for('message', check=lambda m: m.author == ctx.author and m.content.isdigit() and 0 <= int(m.content) <= len(embeds), timeout=30)
                      # await self.bot.wait_for('message')で返ってくるのは文字列型
                        if msg_react.content == "0":
                          # このcontentの中にはゼロ幅スペースが入っています。Noneでもいいのですが編集者はこっちの方が分かりやすいからこうしています。
                            return await msg.edit(content="‌")
                        await msg.edit(content=f"```diff\n{int(msg_react.content)}ページ/{len(embeds)}ページ目を表示中\n見たいページを発言してください。\n30秒経ったら処理は止まります。\n0と発言したら強制的に処理は止まります。```", embed=embeds[int(msg_react.content)-1])
                    except asyncio.TimeoutError: # wait_forの時間制限を超過した場合
                      # このcontentの中にはゼロ幅スペースが入っています。Noneでもいいのですが編集者はこっちの方が分かりやすいからこうしています。
                        return await msg.edit(content="‌", embed=Embed(title=f"時間切れです..."))
            else:
                return await ctx.send(embed=Embed(description=f"{ctx.author.mention}さん...\nこのチャンネルで戦闘は行われてませんよ?"))

        except (NotFound, asyncio.TimeoutError, Forbidden): # 編集した際に文字が見つからなかった, wait_forの時間制限を超過した場合, メッセージに接続できなかった
            return
        except: # 上のERROR以外のERROR出た場合はtracebackで表示するようにしています。 上手くコマンドが反応しない場合はコンソールを見てね！
            return print("エラー情報\n" + traceback.format_exc())

    @commands.command(name="reset", aliases=['re', 'rs'], pass_context=True, description='ユーザーコマンド') # コマンド名:『reset』 省略コマンド:『re, rs』
    @commands.bot_has_permissions(read_messages=True, send_messages=True, embed_links=True, add_reactions=True, manage_messages=True, read_message_history=True) #これ絶対消しちゃダメ
    async def reset(self, ctx): #既に存在する関数名だったらERROR出るのでもし今後コマンドを追加するならコマンド名と同じ関数名にして下さい。
        f"""
        戦闘がそのチャンネルで行われている場合はresetが出来ます。
        戦闘が行われない場合は行われてないというメッセージが返ってきます。
        f"""
        try: # ERRORが起きるか起きないか。起きたらexceptに飛ばされる
          # sqlite_listの中からデータベースに接続したというオブジェクトを取得
            _, conn, cur = [sql for sql in self.bot.sqlite_list if ctx.author.id == sql[0]][0]
          # 戦闘が行われてるかの確認
            await cur.execute("SELECT * FROM in_battle WHERE channel_id=?", (ctx.channel.id,))
            in_battle = await cur.fetchone()
            if in_battle:
                await database.Database().reset_battle(ctx, ctx.channel.id, conn, cur)
                return await conn.commit()
            else:
                return await ctx.send(embed=Embed(description=f"{ctx.author.mention}さん...\nこのチャンネルで戦闘は行われてませんよ?"))

        except (NotFound, asyncio.TimeoutError, Forbidden): # 編集した際に文字が見つからなかった, wait_forの時間制限を超過した場合, メッセージに接続できなかった
            return
        except: # 上のERROR以外のERROR出た場合はtracebackで表示するようにしています。 上手くコマンドが反応しない場合はコンソールを見てね！
            return print("エラー情報\n" + traceback.format_exc())

    @commands.cooldown(1, 3, commands.BucketType.user) #3秒間のクールタイム
    @commands.command(name="t", pass_context=True, description="ユーザーコマンド") # コマンド名:『t』 省略コマンド:『なし』
    @commands.bot_has_permissions(read_messages=True, send_messages=True, embed_links=True, add_reactions=True, manage_messages=True, read_message_history=True) #これ絶対消しちゃダメ
    async def t(self, ctx): #既に存在する関数名だったらERROR出るのでもし今後コマンドを追加するならコマンド名と同じ関数名にして下さい。
        f"""
        トレーニングコマンド。
        training.jsonファイルから問題と答えを持ってきています。
        f"""
        try: # ERRORが起きるか起きないか。起きたらexceptに飛ばされる
          # sqlite_listの中からデータベースに接続したというオブジェクトを取得
            _, conn, cur = [sql for sql in self.bot.sqlite_list if ctx.author.id == sql[0]][0]
            user = ctx.author
            q_id = random.randint(0, 619)
            answer = training_set[q_id][1]
            msg = await ctx.send(embed=Embed(description=f"「{training_set[q_id][0]}」の読み方をひらがなで答えなさい。").set_author(name=f"Training | {user}さんの問題"))
          # 回答メッセージ待ち。答えは[answer]の変数だよ！
            guess = await self.bot.wait_for('message', timeout=15, check=lambda messages: messages.author.id == user.id)
          # await self.bot.wait_for('message')で返ってくるのは文字列型
            if guess.content == answer:
              # プレイヤーの経験値の数をmath.sqrt(平方根)し整数にしてからmath.ceil(切り上げ)を行っております。
                exp = math.ceil(int(math.sqrt(await database.get_player_exp(ctx, user.id, conn, cur))) * 3 / 7)
              # 経験値を足す処理
                comment = await database.experiment(ctx, user.id, exp, conn, cur)
              # 200分の1で『エリクサー』をドロップ
                if random.random() < 0.005:
                    comment += "\n`エリクサー`を手に入れた！"
                    await database.obtain_an_item(conn, cur, user.id, 1)
              # 10分の1で『ファイアボール』をドロップ
                if random.random() < 0.1:
                    comment += "\n`ファイアボールの書`を手に入れた！"
                    await database.obtain_an_item(conn, cur, user.id, 2)
              # 10分の1で『祈りの署』をドロップ
                if random.random() < 0.1:
                    comment += "\n`祈りの書`を手に入れた！"
                    await database.obtain_an_item(conn, cur, user.id, 3)
                await conn.commit()
                return await msg.edit(embed=Embed(description=f"正解だ！{exp}の経験値を得た\n{comment}"))
            else:
                return await msg.edit(embed=Embed(description=f"残念！正解は「{answer}」だ。"))

        except (NotFound, asyncio.TimeoutError, Forbidden): # 編集した際に文字が見つからなかった, wait_forの時間制限を超過した場合, メッセージに接続できなかった
            return
        except: # 上のERROR以外のERROR出た場合はtracebackで表示するようにしています。 上手くコマンドが反応しない場合はコンソールを見てね！
            return print("エラー情報\n" + traceback.format_exc())

    @commands.command(name='ranking', aliases=['rank'], pass_context=True, description='ユーザーコマンド') # コマンド名:『ranking』 省略コマンド:『rank』
    @commands.bot_has_permissions(read_messages=True, send_messages=True, embed_links=True, add_reactions=True, manage_messages=True, read_message_history=True) #これ絶対消しちゃダメ
    async def ranking(self, ctx): #既に存在する関数名だったらERROR出るのでもし今後コマンドを追加するならコマンド名と同じ関数名にして下さい。
        f"""
        各種ランキングの表示
        各種100位まで表示するようにしております。
        10位ごとに勝手にページが分けられます。
        f"""
        try: # ERRORが起きるか起きないか。起きたらexceptに飛ばされる
            bot = self.bot
            r_dict = {'0⃣': "プレイヤーランキング", '1⃣': "BOTランキング",  '2⃣': "鯖ランキング"}
          # sqlite_listの中からデータベースに接続したというオブジェクトを取得
            _, conn, cur = [sql for sql in self.bot.sqlite_list if ctx.author.id == sql[0]][0]
            msg = await ctx.send(embed=Embed(description="\n".join([f"{r[0]}：`{r[1]}`" for r in list(r_dict.items())]) + "\n見たい番号を発言してください。").set_author(name="Ranking一覧:"))
            msg_react = await self.bot.wait_for('message', check=lambda message: message.author == ctx.author and message.content.isdigit() and 0 <= int(message.content) <= len(list(r_dict.keys())) - 1, timeout=10)
          # await self.bot.wait_for('message')で返ってくるのは文字列型
            if msg_react.content == "0":
              # ユーザーはisbotの中身を0で登録してるのでそこで判断して全データを取得させます。
                await cur.execute("select distinct user_id, exp FROM player WHERE isbot =0 ORDER BY exp DESC;")
                players_rank = "\n".join(["{0}位：[`{1}`] (Lv{2})".format(k, bot.get_user(member[0]), int(math.sqrt(member[1]))) for member, k in zip(await cur.fetchall(), range(1, 101))])
              # データ10個ごとにページ分け
                ranking_msgs = ["\n".join(players_rank.split("\n")[i:i + 10]) for i in range(0, 100, 10)]
                author = "世界Top100プレイヤー"
            elif msg_react.content == "1":
              # BOTはisbotの中身を1で登録してるのでそこで判断して全データを取得させます。
                await cur.execute("select distinct user_id, exp FROM player WHERE isbot=1 ORDER BY exp DESC;")
                players_rank = "\n".join(["{0}位：[`{1}`] (Lv{2})".format(k, bot.get_user(member[0]), int(math.sqrt(member[1]))) for member, k in zip(await cur.fetchall(), range(1, 101))])
              # データ10個ごとにページ分け
                ranking_msgs = ["\n".join(players_rank.split("\n")[i:i + 10]) for i in range(0, 100, 10)]
                author = "世界Top100ボット"
            else:
                server_id = []
              # チャンネルのレベル(昇順)にリストを取得します
              # if not [cc for cc in server_id if c[0] in cc] => 既に鯖がリストに入ってる場合は無視するための処理です
              # bot.get_guild(c[0]) => その鯖をBOTが取得できるかの処理です。取得できなかった場合はその鯖の情報は無視されます。
                await cur.execute('select distinct server_id, boss_level FROM channel_status ORDER BY boss_level DESC;')
                [server_id.append(c) for c in await cur.fetchall() if not [cc for cc in server_id if c[0] in cc] and bot.get_guild(c[0])]
                players_rank = "".join(["{0}位：[`{1}`] (Lv{2})\n".format(k, bot.get_guild(c[0]), c[1]) for c, k in zip(server_id, range(1, 101))])
              # データ10個ごとにページ分け
                ranking_msgs = ["\n".join(players_rank.split("\n")[i:i + 10]) for i in range(0, 100, 10)]
                author = "世界Top100サーバー"

            if not list(filter(lambda a: a != '', ranking_msgs)):
                return await ctx.send(embed=Embed(description="まだデータはないようだ..."))

            embeds = []
            for embed in list(filter(lambda a: a != '', ranking_msgs)):
                embeds.append(Embed(description=embed).set_author(name=author))

            await msg.edit(content=f"```diff\n1ページ/{len(embeds)}ページ目を表示中\n見たいページを発言してください。\n30秒経ったら処理は止まります。\n0と発言したら強制的に処理は止まります。```", embed=embeds[0])
            while True: # 処理が終わる(return)まで無限ループ
                try: # ERRORが起きるか起きないか。起きたらexceptに飛ばされる
                    msg_react = await self.bot.wait_for('message', check=lambda m: m.author == ctx.author and m.content.isdigit() and 0 <= int(m.content) <= len(embeds), timeout=30)
                  # await self.bot.wait_for('message')で返ってくるのは文字列型
                    if msg_react.content == "0":
                      # このcontentの中にはゼロ幅スペースが入っています。Noneでもいいのですが編集者はこっちの方が分かりやすいからこうしています。
                        return await msg.edit(content="‌")
                    await msg.edit(content=f"```diff\n{int(msg_react.content)}ページ/{len(embeds)}ページ目を表示中\n見たいページを発言してください。\n30秒経ったら処理は止まります。\n0と発言したら強制的に処理は止まります。```", embed=embeds[int(msg_react.content)-1])
                except asyncio.TimeoutError: # wait_forの時間制限を超過した場合
                  # このcontentの中にはゼロ幅スペースが入っています。Noneでもいいのですが編集者はこっちの方が分かりやすいからこうしています。
                    return await msg.edit(content="‌", embed=Embed(title=f"時間切れです..."))

        except (NotFound, asyncio.TimeoutError, Forbidden): # 編集した際に文字が見つからなかった, wait_forの時間制限を超過した場合, メッセージに接続できなかった
            return
        except: # 上のERROR以外のERROR出た場合はtracebackで表示するようにしています。 上手くコマンドが反応しない場合はコンソールを見てね！
            return print("エラー情報\n" + traceback.format_exc())

def setup(bot): # 絶対必須
    bot.add_cog(command(bot)) # class クラス名(commands.Cog):のクラス名と同じにしないといけない 例:[bot.add_cog(クラス名(bot))]
