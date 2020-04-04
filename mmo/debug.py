 # -*- coding: utf-8 -*-

import asyncio
import io
import traceback
import textwrap
import contextlib
import json
import glob

from discord.ext import commands
from discord import NotFound, Embed,  Forbidden
from .detabase import database
from all_data.all_data import admin_list, prefix

def cleanup_code(content):
    if content.startswith('```') and content.endswith('```'):
        return '\n'.join(content.split('\n')[1:-1])
    return content.strip('` \n')

def get_syntax_error(e):
    if e.text is None:
        return f'```py\n{e.__class__.__name__}: {e}\n```'
    return f'```py\n{e.text}{"^":>{e.offset}}\n{e.__class__.__name__}: {e}```'

def mention_to_user_id(mention):
    user_id = mention.strip("<@").strip(">")
    if user_id.find("!") != -1:
        user_id = user_id.strip("!")
    return int(user_id)

class debug(commands.Cog): #ここのdebugはhelpの時に[{prefix}help コマンド名]としたときにこのファイルのコマンドが指定されたときにクラス名を取得するので変える場合はhelpの中も変えてください。
    def __init__(self, bot):
        self.bot = bot
        self._last_result = None

    @commands.command(name='eval', pass_context=True, description="※運営専用コマンド") # コマンド名:『eval』 省略コマンド:『なし』
    @commands.bot_has_permissions(read_messages=True, send_messages=True, embed_links=True, add_reactions=True, manage_messages=True, read_message_history=True) #これ絶対消しちゃダメ
    async def evals(self, ctx): #既に存在する関数名だったらERROR出るのでもし今後コマンドを追加するならコマンド名と同じ関数名にして下さい。(ここは例外)
        f"""
        evalコマンド。 基本的に何でもできる。
        試しに[{prefix}eval print("a")]って打ってみてほしい。
        そしたら大体どんな感じか理解できるはず！
        f"""
        try: # ERRORが起きるか起きないか。起きたらexceptに飛ばされる
            if ctx.author.id not in admin_list: # BOTの運営かどうかの判断
                return await ctx.send("指定ユーザーのみが使用できます")

            env = {'bot': self.bot, 'ctx': ctx, 'channel': ctx.channel, 'author': ctx.author, 'guild': ctx.guild, 'message': ctx.message, '_': self._last_result}
            env.update(globals())
            body = cleanup_code(ctx.message.content[6:].lstrip())
            stdout = io.StringIO()
            to_compile = f'async def func():\n{textwrap.indent(body, "  ")}'
            try: # ERRORが起きるか起きないか。起きたらexceptに飛ばされる
                exec(to_compile, env)
            except Exception as e:
                return await ctx.send(f'```py\n{e.__class__.__name__}: {e}\n```')
            func = env['func']
            try: # ERRORが起きるか起きないか。起きたらexceptに飛ばされる
                with contextlib.redirect_stdout(stdout):
                    ret = await func()
            except Exception as _:
                value = stdout.getvalue()
                await ctx.send(f'```py\n{value}{traceback.format_exc()}\n```')
            else:
                value = stdout.getvalue()
                try: # ERRORが起きるか起きないか。起きたらexceptに飛ばされる
                    await ctx.message.add_reaction('\u2705')
                except Exception:
                    pass
                if ret is None:
                    if value:
                        await ctx.send(f'```py\n{value}\n```')
                else:
                    self._last_result = ret
                    await ctx.send(f'```py\n{value}{ret}\n```')

        except (NotFound, asyncio.TimeoutError, Forbidden): # 編集した際に文字が見つからなかった, wait_forの時間制限を超過した場合, メッセージに接続できなかった
            return
        except: # 上のERROR以外のERROR出た場合はtracebackで表示するようにしています。 上手くコマンドが反応しない場合はコンソールを見てね！
            return print("エラー情報\n" + traceback.format_exc())

    @commands.command(name='all', pass_context=True, description="※運営専用コマンド") # コマンド名:『all』 省略コマンド:『なし』
    @commands.bot_has_permissions(read_messages=True, send_messages=True, embed_links=True, add_reactions=True, manage_messages=True, read_message_history=True) #これ絶対消しちゃダメ
    async def all(self, ctx, *, user_id:int): #既に存在する関数名だったらERROR出るのでもし今後コマンドを追加するならコマンド名と同じ関数名にして下さい。
        f"""
        ユーザーの全データを削除する
        {prefix}all ユーザーID でユーザーを指定する。
        f"""
        try: # ERRORが起きるか起きないか。起きたらexceptに飛ばされる
            _, conn, cur = [sql for sql in self.bot.sqlite_list if ctx.author.id == sql[0]][0] # sqlite_listの中からデータベースに接続したというオブジェクトを取得
            if ctx.author.id not in admin_list: # BOTの運営かどうかの判断
                return await ctx.send("指定ユーザーのみが使用できます")

            msg = await ctx.send(content=f"<@{ctx.author.id}>これでいいの？\nこの変更で大丈夫な場合は『ok』\nキャンセルの場合は『no』と発言してください。", embed=Embed(description=f"{self.bot.get_user(user_id)}さんの全データを削除してもいいですか？"))
            # okかnoの発言を待つ処理。　もっと待つメッセージを絞る場合はlambdaにしてください。現在はokかnoだけしか認識できません。
            ok_no = await self.bot.wait_for('message', check=lambda m: m.author == ctx.author and m.content.lower() in ["ok", "no"])
            # await self.bot.wait_for('message')で返ってくるのは文字列型
            if ok_no.content.lower() == "ok":  # メッセージがokだった場合
                # 全てのテーブル名をを取得する
                await cur.execute('show tables')
                for user_deta in [str(t[0]) for t in await cur.fetchall()]:
                    # 取得したテーブルのcolumn全てを取得しそのcolumn名の中にuser_idというcolumnがある場合はデータ削除
                    await cur.execute(f"show columns from {user_deta};")
                    if "user_id" in str([c[0] for c in await cur.fetchall()]):
                        await cur.execute(f"DELETE FROM {user_deta} where user_id=?;", (user_id,))
                        await conn.commit() # データベースを最新の情報にするために更新する。 絶対必須
                return await msg.edit(embed=Embed(description=f"{self.bot.get_user(user_id)}さんの全データを削除しました！"))
            else: # メッセージがokではなくnoだった場合
                return await msg.edit(embed=Embed(description=f"{self.bot.get_user(user_id)}さんの全データを削除しませんでした！"))

        except (NotFound, asyncio.TimeoutError, Forbidden): # 編集した際に文字が見つからなかった, wait_forの時間制限を超過した場合, メッセージに接続できなかった
            return
        except: # 上のERROR以外のERROR出た場合はtracebackで表示するようにしています。 上手くコマンドが反応しない場合はコンソールを見てね！
            return print("エラー情報\n" + traceback.format_exc())

    @commands.command(name='db', pass_context=True, description="※運営専用コマンド") # コマンド名:『db』 省略コマンド:『なし』
    @commands.bot_has_permissions(read_messages=True, send_messages=True, embed_links=True, add_reactions=True, manage_messages=True, read_message_history=True) #これ絶対消しちゃダメ
    async def db(self, ctx): #既に存在する関数名だったらERROR出るのでもし今後コマンドを追加するならコマンド名と同じ関数名にして下さい。
        f"""
        {prefix}dbでコマンドの処理を開始。
        対応してる命令文は下記の5つです。
        [SELECT, DELETE, INSERT, UPDATE, SHOW]
        f"""
        try: # ERRORが起きるか起きないか。起きたらexceptに飛ばされる
            _, conn, cur = [sql for sql in self.bot.sqlite_list if ctx.author.id == sql[0]][0] # sqlite_listの中からデータベースに接続したというオブジェクトを取得
            if ctx.author.id not in admin_list: # BOTの運営かどうかの判断
                return await ctx.send("指定ユーザーのみが使用できます")

            msg = await ctx.send(embed=Embed(title=f"接続が完了しました。", description= f"このメッセージの次の発言でそのまま基本命令文を発言してください。"))
            # ここで『select * from player』と打てば全てのユーザーのデータが返ってくる
            msg_react = await self.bot.wait_for('message', check=lambda message: message.author == ctx.author)
            if msg_react.content.split()[0].upper() in ["SELECT", "SHOW"]:
                await cur.execute(msg_react.content)
                all_deta = await cur.fetchall()
                # 全てのデータを10個ごとに分けてページにする
                select_list = ["\n".join("".join([f"[{r}]\n" for r in all_deta]).split("\n")[i:i + 10]) for i in range(0, len(all_deta), 10)]
                if not select_list: # select_listが存在してない場合。つまり空
                    return await msg.edit(embed=Embed(description=f"内容:\n```None```"))

                embeds = []
                for embed in select_list:
                    embeds.append(Embed(description=f"内容:\n```{embed}```"))
                await msg.edit(content=f"```diff\n1ページ/{len(embeds)}ページ目を表示中\n見たいページを発言してください。\n30秒経ったら処理は止まります。\n0と発言したら強制的に処理は止まります。```", embed=embeds[0])
                while True: # 処理が終わる(return)まで無限ループ
                    try: # ERRORが起きるか起きないか。起きたらexceptに飛ばされる
                        msg_react = await self.bot.wait_for('message', check=lambda m: m.author == ctx.author and m.content.isdigit() and 0 <= int(m.content) <= len(embeds), timeout=30)
                        # await self.bot.wait_for('message')で返ってくるのは文字列型
                        if msg_react.content == "0":
                            # このcontentの中にはゼロ幅スペースが入っています。Noneでもいいのですが編集者はこっちの方が分かりやすいからこうしています。
                            return await msg.edit(content="‌")
                        await msg.edit(content=f"```diff\n{int(msg_react.content)}ページ/{len(embeds)}ページ目を表示中\n見たいページを発言してください。\n30秒経ったら処理は止まります。\n0と発言したら強制的に処理は止まります。```", embed=embeds[int(msg_react.content) - 1])
                    except asyncio.TimeoutError: # wait_forの時間制限を超過した場合
                        # このcontentの中にはゼロ幅スペースが入っています。Noneでもいいのですが編集者はこっちの方が分かりやすいからこうしています。
                        return await msg.edit(content="‌", embed=Embed(title=f"時間切れです..."))

            elif msg_react.content.split()[0].upper() in ["DELETE", "UPDATE"]:
                await msg.edit(content=f"<@{ctx.author.id}>これでいいの？\nこの変更で大丈夫な場合は『ok』\nキャンセルの場合は『no』と発言してください。", embed=Embed(description=f"{msg_react.content.split()[0].upper()}内容:\n```{msg_react.content}```"))
                # okかnoの発言を待つ処理。　もっと待つメッセージを絞る場合はlambdaにしてください。現在はokかnoだけしか認識できません。
                ok_no = await self.bot.wait_for('message', check=lambda m: m.author == ctx.author and m.content.lower() in ["ok", "no"])
                # await self.bot.wait_for('message')で返ってくるのは文字列型
                if ok_no.content.lower() == "ok":  # メッセージがokだった場合
                    await cur.execute(msg_react.content)
                    await conn.commit()
                    return await msg.edit(embed=Embed(description=f"入力されたデータを{msg_react.content.split()[0].upper()}しました！"))
                else: # メッセージがokではなくnoだった場合
                    return await msg.edit(embed=Embed(description=f"入力されたデータを{msg_react.content.split()[0].upper()}しませんでした！"))

            elif msg_react.content.split()[0].upper() == "INSERT":
                await msg.edit(content=f"<@{ctx.author.id}>これでいいの？\nこの変更で大丈夫な場合は『ok』\nキャンセルの場合は『no』と発言してください。", embed=Embed(description=f"追加データ内容:\n```{msg_react.content}```"))
                # okかnoの発言を待つ処理。　もっと待つメッセージを絞る場合はlambdaにしてください。現在はokかnoだけしか認識できません。
                ok_no = await self.bot.wait_for('message', check=lambda m: m.author == ctx.author and m.content.lower() in ["ok", "no"])
                # await self.bot.wait_for('message')で返ってくるのは文字列型
                if ok_no.content.lower() == "ok": # メッセージがokだった場合
                    await cur.execute(msg_react.content)
                    await conn.commit()
                    return await msg.edit(embed=Embed(description=f"入力されたデータをINSERTしました！"))
                else: # メッセージがokではなくnoだった場合
                    return await msg.edit(embed=Embed(description=f"入力されたデータをINSERTしませんでした！"))
            else:
                return await msg.edit(embed=Embed(description=f"ERROR...これは出力できません。\n設定されている基本命令文は下のやつだけです。\n[SELECT, DELETE, INSERT, UPDATE, SHOW]"))

        except (NotFound, asyncio.TimeoutError, Forbidden): # 編集した際に文字が見つからなかった, wait_forの時間制限を超過した場合, メッセージに接続できなかった
            return
        except: # 上のERROR以外のERROR出た場合はtracebackで表示するようにしています。 上手くコマンドが反応しない場合はコンソールを見てね！
            return print("エラー情報\n" + traceback.format_exc())

    @commands.command(name='zukan', pass_context=True, description="※運営専用コマンド") # コマンド名:『zukan』 省略コマンド:『なし』
    @commands.bot_has_permissions(read_messages=True, send_messages=True, embed_links=True, add_reactions=True, manage_messages=True, read_message_history=True) #これ絶対消しちゃダメ
    async def zukan(self, ctx): #既に存在する関数名だったらERROR出るのでもし今後コマンドを追加するならコマンド名と同じ関数名にして下さい。
        f"""
        monsterファイルから現在登録されてるモンスターリストを引っ張ってくる。
        もし今後ファイルを追加する場合は[zokusei, files]の変数にあたる["通常", "レア"], ["normal", "rera"]でレアリティとファイル名を追加してください。
        f"""
        try: # ERRORが起きるか起きないか。起きたらexceptに飛ばされる
            _, conn, cur = [sql for sql in self.bot.sqlite_list if ctx.author.id == sql[0]][0] # sqlite_listの中からデータベースに接続したというオブジェクトを取得
            if ctx.author.id not in admin_list: # BOTの運営かどうかの判断
                return await ctx.send("指定ユーザーのみが使用できます")

            monster_list = []
            alphabet, react, zokusei, files = list("abcdefghijklmnopqrstuvwxyz"), list("🇦🇧🇨🇩🇪🇫🇬🇭🇮🇯🇰🇱🇲🇳🇴🇵🇶🇷🇸🇹🇺🇻🇼🇽🇾🇿"), ["通常", "レア"], ["normal", "rera"]
            # {r[1][3]}体で何体居るのかを表示するための処理
            monster_count = []
            for m in files:
                for file1 in glob.glob(f"./monster/{m}.json"):
                    with open(r'' + file1 + '', encoding='utf-8') as fh1:
                        monster_count.append(len([xx for xx in json.loads(str(fh1.read()).replace('True', 'true').replace('False', 'false'))]))

            d = {k: [v.encode('utf-8'), a, aa, m] for (k, v, a, aa, m) in zip(alphabet, react, zokusei, files, monster_count)} # zukan専用の辞書を作成
            msg = await ctx.send(embed=Embed(description="\n".join([f"{r[1][0].decode('utf-8')}：`{r[1][1]}属性 | {r[1][3]}体`" for r in list(d.items())]) + "\n見たいアルファベットを発言してください。").set_author(name="敵図鑑一覧:"))
            m = await self.bot.wait_for('message', check=lambda mm: mm.author == ctx.author and mm.content.lower() in list(d.keys()))
            # await self.bot.wait_for('message')で返ってくるのは文字列型
            for file1 in glob.glob(f"./monster/{d.get(m.content.lower())[2]}.json"):
                with open(r'' + file1 + '', encoding='utf-8') as fh1:
                    json_txt1 = str(fh1.read()).replace('True', 'true').replace('False', 'false')
                    [monster_list.append(xx) for xx in json.loads(json_txt1)]

            embeds = []
            for m in monster_list:
                embeds.append(Embed(description=f"モンスター名:「{m['name']}」| ランク:{m['rank']}").set_thumbnail(url=self.bot.user.avatar_url_as()).set_image(url=m["img"]).set_footer(text=f"合計:{len(monster_list)}体"))

            await msg.edit(content=f"```diff\n1ページ/{len(embeds)}ページ目を表示中\n見たいページを発言してください。\n30秒経ったら処理は止まります。\n0と発言したら強制的に処理は止まります。```", embed=embeds[0])
            while True: # 処理が終わる(return)まで無限ループ
                try: # ERRORが起きるか起きないか。起きたらexceptに飛ばされる
                    msg_react = await self.bot.wait_for('message', check=lambda mm: mm.author == ctx.author and mm.content.isdigit() and 0 <= int(mm.content) <= len(embeds), timeout=30)
                    # await self.bot.wait_for('message')で返ってくるのは文字列型
                    if msg_react.content == "0":
                        # このcontentの中にはゼロ幅スペースが入っています。Noneでもいいのですが編集者はこっちの方が分かりやすいからこうしています。
                        return await msg.edit(content="‌")
                    await msg.edit(content=f"```diff\n{int(msg_react.content)}ページ/{len(embeds)}ページ目を表示中\n見たいページを発言してください。\n30秒経ったら処理は止まります。\n0と発言したら強制的に処理は止まります。```", embed=embeds[int(msg_react.content) - 1])
                except asyncio.TimeoutError: # wait_forの時間制限を超過した場合
                    # このcontentの中にはゼロ幅スペースが入っています。Noneでもいいのですが編集者はこっちの方が分かりやすいからこうしています。
                    return await msg.edit(content="‌", embed=Embed(title=f"時間切れです..."))

        except (NotFound, asyncio.TimeoutError, Forbidden): # 編集した際に文字が見つからなかった, wait_forの時間制限を超過した場合, メッセージに接続できなかった
            return
        except: # 上のERROR以外のERROR出た場合はtracebackで表示するようにしています。 上手くコマンドが反応しない場合はコンソールを見てね！
            return print("エラー情報\n" + traceback.format_exc())

    @commands.command(name='exp', pass_context=True, description="※運営専用コマンド") # コマンド名:『exp』 省略コマンド:『なし』
    @commands.bot_has_permissions(read_messages=True, send_messages=True, embed_links=True, add_reactions=True, manage_messages=True, read_message_history=True) #これ絶対消しちゃダメ
    async def exp(self, ctx, mention, exp:int): #既に存在する関数名だったらERROR出るのでもし今後コマンドを追加するならコマンド名と同じ関数名にして下さい。
        f"""
        メンションしたユーザーに指定したEXPを付与する。 [-も対応]
        {prefix}exp @兄じゃぁぁぁ # 3454 100
        これで兄じゃぁぁぁさんに100expを付与する。レベルもちゃんと上がる。
        f"""
        try: # ERRORが起きるか起きないか。起きたらexceptに飛ばされる
            _, conn, cur = [sql for sql in self.bot.sqlite_list if ctx.author.id == sql[0]][0] # sqlite_listの中からデータベースに接続したというオブジェクトを取得
            if ctx.author.id not in admin_list: # BOTの運営かどうかの判断
                return await ctx.send("指定ユーザーのみが使用できます")
            test = await database.experiment(ctx, mention_to_user_id(mention), exp, conn, cur) # 経験値を足す処理とメンションからユーザーIDを取得する処理
            await conn.commit() # データベースを最新の情報にするために更新する。 絶対必須
            return await ctx.send(embed=Embed(description=f"{ctx.author}は{mention}に{exp}expを付与した\n{str(test)}"))

        except (NotFound, asyncio.TimeoutError, Forbidden): # 編集した際に文字が見つからなかった, wait_forの時間制限を超過した場合, メッセージに接続できなかった
            return
        except: # 上のERROR以外のERROR出た場合はtracebackで表示するようにしています。 上手くコマンドが反応しない場合はコンソールを見てね！
            return print("エラー情報\n" + traceback.format_exc())

    @commands.command(name='ban', pass_context=True, description="※運営専用コマンド") # コマンド名:『ban』 省略コマンド:『なし』
    @commands.bot_has_permissions(read_messages=True, send_messages=True, embed_links=True, add_reactions=True, manage_messages=True, read_message_history=True) #これ絶対消しちゃダメ
    async def ban(self, ctx, user_id:int): #既に存在する関数名だったらERROR出るのでもし今後コマンドを追加するならコマンド名と同じ関数名にして下さい。
        f"""
        ユーザーをBANする。
        {prefix}ban ユーザーID でユーザーを指定する。
        f"""
        try: # ERRORが起きるか起きないか。起きたらexceptに飛ばされる
            _, conn, cur = [sql for sql in self.bot.sqlite_list if ctx.author.id == sql[0]][0] # sqlite_listの中からデータベースに接続したというオブジェクトを取得
            if ctx.author.id not in admin_list: # BOTの運営かどうかの判断
                return await ctx.send("指定ユーザーのみが使用できます")

            user = self.bot.get_user(user_id)
            msg = await ctx.send(content=f"<@{ctx.author.id}>これでいいの？\nこの変更で大丈夫な場合は『ok』\nキャンセルの場合は『no』と発言してください。", embed=Embed(description=f"{self.bot.user}からこの人をBANしても良いですか??\nBANする相手:{user}"))
            # okかnoの発言を待つ処理。　もっと待つメッセージを絞る場合はlambdaにしてください。現在はokかnoだけしか認識できません。
            ok_no = await self.bot.wait_for('message', check=lambda m: m.author == ctx.author and m.content.lower() in ["ok", "no"])
            # await self.bot.wait_for('message')で返ってくるのは文字列型
            if ok_no.content.lower() == "ok": # メッセージがokだった場合
                await cur.execute("INSERT INTO ban_user(user_id) VALUES(?);", (user_id,)) # ユーザーをBANする
                await conn.commit() # データベースを最新の情報にするために更新する。 絶対必須
                return await msg.edit(embed=Embed(description=f"{user}さんをBANしました！"))
            else: # メッセージがokではなくnoだった場合
                return await msg.edit(embed=Embed(description=f"{user}さんをBANしませんでした！"))

        except (NotFound, asyncio.TimeoutError, Forbidden): # 編集した際に文字が見つからなかった, wait_forの時間制限を超過した場合, メッセージに接続できなかった
            return
        except: # 上のERROR以外のERROR出た場合はtracebackで表示するようにしています。 上手くコマンドが反応しない場合はコンソールを見てね！
            return print("エラー情報\n" + traceback.format_exc())

    @commands.command(name='unban', pass_context=True, description="※運営専用コマンド") # コマンド名:『unban』 省略コマンド:『なし』
    @commands.bot_has_permissions(read_messages=True, send_messages=True, embed_links=True, add_reactions=True, manage_messages=True, read_message_history=True) #これ絶対消しちゃダメ
    async def unban(self, ctx, user_id:int): #既に存在する関数名だったらERROR出るのでもし今後コマンドを追加するならコマンド名と同じ関数名にして下さい。
        f"""
        BANされている人を解除する。
        {prefix}unban ユーザーID でユーザーを指定する。
        f"""
        try: # ERRORが起きるか起きないか。起きたらexceptに飛ばされる
            _, conn, cur = [sql for sql in self.bot.sqlite_list if ctx.author.id == sql[0]][0] # sqlite_listの中からデータベースに接続したというオブジェクトを取得
            if ctx.author.id not in admin_list: # BOTの運営かどうかの判断
                return await ctx.send("指定ユーザーのみが使用できます")

            user = self.bot.get_user(user_id)
            msg = await ctx.send(content=f"<@{ctx.author.id}>これでいいの？\nこの変更で大丈夫な場合は『ok』\nキャンセルの場合は『no』と発言してください。", embed=Embed(description=f"{self.bot.user}からこの人をBANしても良いですか??\nBANする相手:{user}"))
            # okかnoの発言を待つ処理。　もっと待つメッセージを絞る場合はlambdaにしてください。現在はokかnoだけしか認識できません。
            ok_no = await self.bot.wait_for('message', check=lambda m: m.author == ctx.author and m.content.lower() in ["ok", "no"])
            # await self.bot.wait_for('message')で返ってくるのは文字列型
            if ok_no.content.lower() == "ok": # メッセージがokだった場合
                await cur.execute("delete from ban_user where user_id=?;", (user_id,)) #ユーザーのBANを解除！
                await conn.commit() # データベースを最新の情報にするために更新する。 絶対必須
                return await msg.edit(embed=Embed(description=f"{user}さんをUNBANしました！"))
            else: # メッセージがokではなくnoだった場合
                return await msg.edit(embed=Embed(description=f"{user}さんをUNBANしませんでした！"))

        except (NotFound, asyncio.TimeoutError, Forbidden): # 編集した際に文字が見つからなかった, wait_forの時間制限を超過した場合, メッセージに接続できなかった
            return
        except: # 上のERROR以外のERROR出た場合はtracebackで表示するようにしています。 上手くコマンドが反応しない場合はコンソールを見てね！
            return print("エラー情報\n" + traceback.format_exc())

    @commands.command(name="database", pass_context=True, description='運営専用コマンド') # コマンド名:『database』 省略コマンド:『なし』
    @commands.bot_has_permissions(read_messages=True, send_messages=True, embed_links=True, add_reactions=True, manage_messages=True, read_message_history=True) #これ絶対消しちゃダメ
    async def database(self, ctx, *, content=""): #既に存在する関数名だったらERROR出るのでもし今後コマンドを追加するならコマンド名と同じ関数名にして下さい。
        f"""
        databaseを作成する
        {prefix}database createで最低限のデータベースを作成します。
        {prefix}database dropでデータベースの中身を全て消します。
        f"""
        try: # ERRORが起きるか起きないか。起きたらexceptに飛ばされる
            _, conn, cur = [sql for sql in self.bot.sqlite_list if ctx.author.id == sql[0]][0] # sqlite_listの中からデータベースに接続したというオブジェクトを取得
            if ctx.author.id not in admin_list: # BOTの運営かどうかの判断
                return await ctx.send("指定ユーザーのみが使用できます")

            if content.upper() == "CREATE":
                msg = await ctx.send(content=f"大丈夫な場合は『ok』\nキャンセルの場合は『no』と発言してください。", embed=Embed(description=f"データベースを作成しますか？"))
                # okかnoの発言を待つ処理。　もっと待つメッセージを絞る場合はlambdaにしてください。現在はokかnoだけしか認識できません。
                ok_no = await self.bot.wait_for('message', check=lambda m: m.author == ctx.author and m.content.lower() in ["ok", "no"])
                # await self.bot.wait_for('message')で返ってくるのは文字列型
                if ok_no.content.lower() == "ok": # メッセージがokだった場合
                    await conn.commit() # データベースを最新の情報にするために更新する。 絶対必須
                    # テーブル名:『player』 カラム内容： ユーザーID 整数型, 経験値 整数型, ボットか否か 整数型
                    await cur.execute("CREATE TABLE IF NOT EXISTS player(user_id BIGINT(20), exp bigint(20), isbot int)")
                    await conn.commit() # データベースを最新の情報にするために更新する。 絶対必須

                    # テーブル名:『item』 カラム内容： ユーザーID 整数型, アイテムID　整数値, 個数 整数値
                    await cur.execute("CREATE TABLE IF NOT EXISTS item(user_id BIGINT(20), item_id INT, count INT)")
                    await conn.commit() # データベースを最新の情報にするために更新する。 絶対必須

                    # テーブル名:『ban_user』 カラム内容： ユーザーID 整数型
                    await cur.execute("CREATE TABLE IF NOT EXISTS ban_user(user_id BIGINT(20))")
                    await conn.commit() # データベースを最新の情報にするために更新する。 絶対必須

                    # テーブル名:『in_battle』 カラム内容： ユーザーID 整数型, チャンネルID 整数型, 自分の体力 整数型
                    await cur.execute("CREATE TABLE IF NOT EXISTS in_battle(user_id BIGINT(20), channel_id BIGINT(20), player_hp INT)")
                    await conn.commit() # データベースを最新の情報にするために更新する。 絶対必須

                    # テーブル名:『channel_status』 カラム内容： サーバーID 整数型 , チャンネルID 整数型 , 敵のレベル 整数型 , 敵の体力 整数型
                    await cur.execute("CREATE TABLE IF NOT EXISTS channel_status(server_id bigint(20), channel_id BIGINT(20), boss_level INT, boss_hp INT)")
                    await conn.commit() # データベースを最新の情報にするために更新する。 絶対必須

                    return await msg.edit(embed=Embed(description=f"{ctx.author.mention}さん...\nデータベースを作成しました！"))
                else: # メッセージがokではなくnoだった場合
                    return await msg.edit(embed=Embed(description=f"{ctx.author.mention}さん...\nデータベースを作成しませんでした！"))

            elif content.upper() == "DROP":
                msg = await ctx.send(content=f"大丈夫な場合は『ok』\nキャンセルの場合は『no』と発言してください。", embed=Embed(description=f"データベースを作成しますか？"))
                # okかnoの発言を待つ処理。　もっと待つメッセージを絞る場合はlambdaにしてください。現在はokかnoだけしか認識できません。
                ok_no = await self.bot.wait_for('message', check=lambda m: m.author == ctx.author and m.content.lower() in ["ok", "no"])
                # await self.bot.wait_for('message')で返ってくるのは文字列型
                if ok_no.content.lower() == "ok": # メッセージがokだった場合
                    for table in ["player", "item", "in_battle", "channel_status", "ban_user"]:
                        await cur.execute(f"DROP TABLE {table};")
                        await conn.commit()
                        return await msg.edit(embed=Embed(description=f"{ctx.author.mention}さん...\nデータベースを削除しました！"))
                else: # メッセージがokではなくnoだった場合
                    return await msg.edit(embed=Embed(description=f"{ctx.author.mention}さん...\nデータベースを削除しませんでした！"))

            else: # メッセージがcreateでもdropでもなかった場合
                return await ctx.send(embed=Embed(description=f"{prefix}database [create, drop]の2つしか対応してないよ！"))

        except (NotFound, asyncio.TimeoutError, Forbidden): # 編集した際に文字が見つからなかった, wait_forの時間制限を超過した場合, メッセージに接続できなかった
            return
        except: # 上のERROR以外のERROR出た場合はtracebackで表示するようにしています。 上手くコマンドが反応しない場合はコンソールを見てね！
            return print("エラー情報\n" + traceback.format_exc())

def setup(bot): # 絶対必須
    bot.add_cog(debug(bot)) # class クラス名(commands.Cog):のクラス名と同じにしないといけない 例:[bot.add_cog(クラス名(bot))]
