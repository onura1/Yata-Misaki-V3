# commands/Owner/ping.py
import discord
from discord.ext import commands
import time
# import logging # Loglama kaldırıldı

class PingCog(commands.Cog, name="Ping Komutu (Sahip)"): # Yardım komutunun tanıması için Cog adı güncellendi
    """Botun gecikme süresini gösteren komut (Sadece Sahip)."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="ping", aliases=["gecikme"])
    @commands.is_owner() # Sadece sahip kullanabilir
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def ping(self, ctx: commands.Context):
        """Botun Discord API'sine olan gecikmesini gösterir (Sadece Sahip)."""
        start_monotonic = time.monotonic()
        msg = await ctx.send("🏓 Pong!")
        end_monotonic = time.monotonic()
        websocket_latency = self.bot.latency * 1000
        roundtrip_latency = (end_monotonic - start_monotonic) * 1000
        await msg.edit(content=f"🏓 Pong!\n"
                               f"🔹 WebSocket Gecikmesi: **{websocket_latency:.2f}ms**\n"
                               f"🔸 Mesaj Gidiş-Geliş Süresi: **{roundtrip_latency:.2f}ms**")

    @ping.error
    async def ping_error(self, ctx: commands.Context, error):
        if isinstance(error, commands.NotOwner):
             await ctx.send("❌ Bu komutu sadece bot sahibi kullanabilir!")
        elif isinstance(error, commands.CommandOnCooldown):
            await ctx.send(f"⏳ Bu komutu tekrar kullanmak için lütfen {error.retry_after:.1f} saniye bekleyin.", delete_after=5)
        else:
            print(f"[HATA] Ping komutunda hata: {error}") # logger yerine print
            await ctx.send(f"❓ Ping komutunda bir hata oluştu.")

async def setup(bot: commands.Bot):
    await bot.add_cog(PingCog(bot))
    print("✅ Owner/Ping Cog yüklendi!")