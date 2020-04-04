#!/usr/bin/env python3.7-4
# -*- coding: utf-8 -*-

import traceback

from discord.ext import commands
from discord import Game
from aiosqlite import connect
from all_data.all_data import prefix

class system(commands.Cog):
    def __init__(self, bot):
        self.bot = bot # 親ファイル(run.py)ではselfだけで十分なのだがmmoディレクトリのcogsのファイルたちはself.botとしないといけない。

    @commands.Cog.listener() # これは絶対に絶対に必要消したらだめ Cogsの中でon_関数系をする場合はこれがないとダメ
    async def on_channel_remove(self, channel): #　このBOTが認識できる範囲の中でチャンネルが削除された場合
        try: # ERRORが起きるか起きないか。起きたらexceptに飛ばされる
            async with connect('./all_data/mmo.db') as conn: # データベースに接続
                async with conn.cursor() as cur:
                    # 全てのテーブル名をを取得する
                    await cur.execute('show tables')
                    for user_deta in [str(t[0]) for t in await cur.fetchall()]:
                        # 取得したテーブルのcolumn全てを取得しそのcolumn名の中にchannel_idというcolumnがある場合はデータ削除
                        await cur.execute(f"show columns from {user_deta};")
                        if "user_id" in str([c[0] for c in await cur.fetchall()]):
                            await cur.execute(f"DELETE FROM {user_deta} where channel_id=%s;", (channel.id,))
                            await conn.commit() # データベースを最新の情報にするために更新する。 絶対必須

        except: # 上のERROR以外のERROR出た場合はtracebackで表示するようにしています。 上手くコマンドが反応しない場合はコンソールを見てね！
            return print("エラー情報\n" + traceback.format_exc())

    @commands.Cog.listener() # これは絶対に絶対に必要消したらだめ Cogsの中でon_関数系をする場合はこれがないとダメ
    async def on_guild_join(self, _): #　このBOtが鯖に追加された場合の処理
        try: # ERRORが起きるか起きないか。起きたらexceptに飛ばされる
            if self.bot.only_admin: # self.bot.only_adminが存在している場合
                return await self.bot.change_presence(activity=Game(name=f"現在運営しか使用できません。", type=1)) # BOTのステータス変更
            else: # 存在してなかった
                return await self.bot.change_presence(activity=Game(name=f"{prefix}help | {len(self.bot.guilds)}guilds", type=1)) # BOTのステータス変更
        except: # 上のERROR以外のERROR出た場合はtracebackで表示するようにしています。 上手くコマンドが反応しない場合はコンソールを見てね！
            return print("エラー情報\n" + traceback.format_exc())

    @commands.Cog.listener() # これは絶対に絶対に必要消したらだめ Cogsの中でon_関数系をする場合はこれがないとダメ
    async def on_guild_remove(self, _): #　このBOtが鯖に追加された場合の処理
        try: # ERRORが起きるか起きないか。起きたらexceptに飛ばされる
            if self.bot.only_admin: # self.bot.only_adminが存在している場合
                return await self.bot.change_presence(activity=Game(name=f"現在運営しか使用できません。", type=1)) # BOTのステータス変更
            else: # 存在してなかった
                return await self.bot.change_presence(activity=Game(name=f"{prefix}help | {len(self.bot.guilds)}guilds", type=1)) # BOTのステータス変更
        except: # 上のERROR以外のERROR出た場合はtracebackで表示するようにしています。 上手くコマンドが反応しない場合はコンソールを見てね！
            return print("エラー情報\n" + traceback.format_exc())

def setup(bot): # 絶対必須
    bot.add_cog(system(bot)) # class クラス名(commands.Cog):のクラス名と同じにしないといけない 例:[bot.add_cog(クラス名(bot))]
