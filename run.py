 # -*- coding: utf-8 -*-
import os

from discord.ext import commands
from discord import Embed, Forbidden, Game
from threading import Thread
from aiosqlite import connect
from asyncio import new_event_loop
from traceback import format_exc
from all_data.all_data import token, prefix, admin_list

all_commands_user, all_commands_channel = [], []
loop = new_event_loop()

async def run():
    if not prefix: #prefixが設定されてない場合
        return print(f"""prefixを設定してね！ TAOボットで言う[{prefix}]みたいなもんだよ！ "./all_data/setting.json"で設定可能！f""")

    # only_adminの[]に["a"]等とした場合はボット運営のみ使用可能となります。
    sqlite_list, on_ready_complete, only_admin, ban_member = [], [], [], []
    bot = MyBot(sqlite_list=sqlite_list, on_ready_complete=on_ready_complete, only_admin=only_admin, ban_member=ban_member)
    try: # ERRORが起きるか起きないか。起きたらexceptに飛ばされる
        if not os.path.exists("./all_data/mmo.db"):
            # ./all_data/mmo.dbが存在してない場合は自動的に作成されます。
            # そして自動的に現段階で必要な環境にします。
            open(f"./all_data/mmo.db", "w").close() # 存在しない場合は./all_data/mmo.dbが作成される
            async with connect('./all_data/mmo.db') as conn: # データベースに接続
                async with conn.cursor() as cur:
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

        try: # ERRORが起きるか起きないか。起きたらexceptに飛ばされる
            await bot.start(token) # BOTを起動させる
        except: # tokenが違った場合
            return print("このtokenは読み込まれなかったよ！")
    except KeyboardInterrupt:
        await bot.logout() # BOTをログアウトさせる
    except: # 上のERROR以外のERROR出た場合はtracebackで表示するようにしています。 上手くコマンドが反応しない場合はコンソールを見てね！
        return print("エラー情報\n" + format_exc())

class MyBot(commands.Bot):
    def __init__(self, **kwargs):
        super().__init__(command_prefix=commands.when_mentioned_or(prefix), fetch_offline_members=False, pm_help=None, help_attrs=dict(hidden=True), loop=loop)
        self.sqlite_list = kwargs.pop("sqlite_list")
        self.on_ready_complete = kwargs.pop("on_ready_complete")
        self.only_admin = kwargs.pop("only_admin")
        self.ban_member = kwargs.pop("ban_member")
        self.remove_command('help') # helpコマンドを除外
        [self.load_extension(f'mmo.{c}') for c in ["command", "debug", "system"]] # mmoディレクトリからファイルを読み込む

    def remove_from_list(self, u_id, c_id):
        [all_commands_user.remove(u) for u in all_commands_user if u in all_commands_user and u == u_id]
        [all_commands_channel.remove(c) for c in all_commands_channel if c in all_commands_channel and c == c_id]
        [self.sqlite_list.remove(m) for m in self.sqlite_list if u_id == m[0]]

    async def on_ready(self): # BOTが完全に起動したら通る関数
        try: # ERRORが起きるか起きないか。起きたらexceptに飛ばされる
            print(self.user.name, self.user.id) # 起動したときにボットの名前とIDをprint
            self.on_ready_complete.append("ready") # self.on_ready_completeに何かしらの何かを追加　これをしないとon_message関数が動かない
            if self.only_admin: # self.only_adminが存在している場合
                return await self.change_presence(activity=Game(name=f"現在運営しか使用できません。", type=1)) # BOTのステータス変更
            else: # 存在してなかった
                return await self.change_presence(activity=Game(name=f"{prefix}help | {len(self.guilds)}guilds", type=1)) # BOTのステータス変更
        except: # 上のERROR以外のERROR出た場合はtracebackで表示するようにしています。 上手くコマンドが反応しない場合はコンソールを見てね！
            return print("エラー情報\n" + format_exc())

    async def on_message(self, message): # on_message内でのreturnは自分の書き方では挙動がおかしくなるのでなるべく控えて下さい。
        if not self.on_ready_complete: # on_ready関数が通ったらself.on_ready_completeを通るようになる
            return # ここのreturnは必須
        try: # ERRORが起きるか起きないか。起きたらexceptに飛ばされる
            author = message.author
            user_id = message.author.id
            channel_id = message.channel.id
            if user_id in self.ban_member: # ban_memberにユーザーが登録されている場合
                await message.channel.send(embed=Embed(description=f"{message.author.mention}さん.......\nBANされてますよ？"))
            else:
                # message.content.startswith(prefix) => もしメッセージの最初が設定したprefixではない場合
                # not message.webhook_id => メッセージがwebhookではない場合。
                # author != self.user => メッセージ発言者が 現在動かしてるBOTではない場合
                # (self.only_admin and user_id in admin_list) => self.only_adminが存在してて(デフォルトは[]なので空)なおかつadmin_listの中に自分のIDが存在してる場合
                if message.content.startswith(prefix) and not message.webhook_id and author != self.user or (self.only_admin and user_id in admin_list):
                    if user_id in all_commands_user or channel_id in all_commands_channel: # コマンドがまだ実行中の場合
                        await message.channel.send("`コマンド失敗。ゆっくりコマンドを打ってね。`")
                    else:
                        all_commands_user.append(user_id)
                        all_commands_channel.append(channel_id)
                        async with connect('./all_data/mmo.db') as conn: # データベースに接続
                            async with conn.cursor() as cur:
                                self.sqlite_list.append([user_id, conn, cur])
                                thread = Thread(target=await self.process_commands(message)) # コマンドの処理が終わるまで次のコマンドが行われないように待機(多重敵殺しなどを防ぐため)
                                thread.start() # コマンドの処理を開始
                                thread.join() # コマンドが終わるまで次の処理を行けない。
                                self.remove_from_list(user_id, channel_id) # 処理が終わったので次のコマンドを通せるようにリストから指定のデータを削除

        except: # 上のERROR以外のERROR出た場合はtracebackで表示するようにしています。 上手くコマンドが反応しない場合はコンソールを見てね！
            return print("エラー情報\n" + format_exc())

    f"""この下の#を取ればBOTでも遊べるようになります。f"""
    #async def process_commands(self, message):
    #    if not self.on_ready_complete: # on_ready関数が通ったらself.on_ready_completeを通るようになる
    #        return # ここのreturnは必須
    #    try: # ERRORが起きるか起きないか。起きたらexceptに飛ばされる
    #        ctx = await self.get_context(message)
    #        await self.invoke(ctx)
    #    except:
    #        return print("エラー情報\n" + traceback.format_exc())

    async def on_command_error(self, ctx, e):
        if not self.on_ready_complete: # on_ready関数が通ったらself.on_ready_completeを通るようになる
            return # ここのreturnは必須
        try: # ERRORが起きるか起きないか。起きたらexceptに飛ばされる
            # コマンドが存在してない場合
            if isinstance(e, commands.CommandNotFound):
                return await ctx.send(embed=Embed(description=f"そのコマンドは存在しません。"))
            # @commands.bot_has_permissions(read_messages=True, send_messages=True, embed_links=True, add_reactions=True, manage_messages=True, read_message_history=True)
            # コマンドの場所で上記のように書かれてると思いますがBOTにその権限が無い場合にこのERRORになります。
            elif isinstance(e, commands.BotMissingPermissions):
                permission = {'read_messages': "メッセージを読む", 'send_messages': "メッセージを送信", 'read_message_history': "メッセージ履歴を読む", 'manage_messages': "メッセージの管理", 'embed_links': "埋め込みリンク", 'add_reactions': "リアクションの追加"}
                text = ""
                for all_error_permission in e.missing_perms: # 大丈夫ではない権限を判断
                    text += f"❌:{permission[all_error_permission]}\n"
                    del permission[all_error_permission] # permissionからダメな権限を除外
                for all_arrow_permission in list(permission.values()): # 残りの権限は大丈夫なのでそれをチェックにする
                    text += f"✅:{all_arrow_permission}\n"
                try: # ERRORが起きるか起きないか。起きたらexceptに飛ばされる
                    await ctx.author.send(embed=Embed(description=text).set_author(name=f"『{ctx.guild.name}』での{self.user}の必要な権限:")) # ユーザーのDMに送る。しかし送れる権限がない場合は何もなかったことにされる^^
                except Exception:
                    return
            elif isinstance(e, commands.CommandOnCooldown):
                return await ctx.send(embed=Embed(description="まだこのコマンドのクールタイムは終わってません！\n`{:.2f}`秒後にまたお願いします！".format(e.retry_after)))
            else:
                raise e

        except Forbidden:
            return
        except: # 上のERROR以外のERROR出た場合はtracebackで表示するようにしています。 上手くコマンドが反応しない場合はコンソールを見てね！
            return print("エラー情報\n" + format_exc())

if __name__ == '__main__':
    main_task = loop.create_task(run())
    loop.run_until_complete(main_task)
    loop.close()
