# commands/Owner/uptime.py (Owner Klasörüne Taşındı ve Sahip Kontrolü Eklendi)
import discord
from discord.ext import commands
import time
import datetime
# import logging # Loglama kaldırıldı

class UptimeCog(commands.Cog, name="Aktiflik Süresi (Sahip)"): # Yardım komutunun tanıması için Cog adı güncellendi
    """Botun ne kadar süredir aktif olduğunu gösteren komut (Sadece Sahip)."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # self.logger = logging.getLogger(__name__) # Loglama kaldırıldı

    @commands.command(name="uptime", aliases=["aktiflik"])
    @commands.is_owner() # Sadece sahip kullanabilir
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def uptime(self, ctx: commands.Context):
        """Botun ne kadar süredir aktif olduğunu gösterir (Sadece Sahip)."""
        if not hasattr(self.bot, 'start_time') or self.bot.start_time is None:
             print("[UYARI] Uptime komutu çağrıldı ancak bot.start_time bulunamadı.") # logger yerine print
             await ctx.send("❌ Bot başlangıç zamanı bilgisi alınamadı!")
             return

        try:
            current_time = time.time()
            difference_seconds = int(round(current_time - self.bot.start_time))
            formatted_duration = str(datetime.timedelta(seconds=difference_seconds))
            await ctx.send(f"⏳ Bot **{formatted_duration}** süredir aktif.")
        except Exception as e:
            print(f"[HATA] Uptime komutunda timedelta hatası veya gönderme hatası: {e}") # logger yerine print
            await ctx.send("Uptime hesaplanırken bir sorun oluştu.")

    @uptime.error
    async def uptime_error(self, ctx: commands.Context, error):
        if isinstance(error, commands.NotOwner):
             await ctx.send("❌ Bu komutu sadece bot sahibi kullanabilir!")
        elif isinstance(error, commands.CommandOnCooldown):
            await ctx.send(f"⏳ Bu komutu tekrar kullanmak için lütfen {error.retry_after:.1f} saniye bekleyin.", delete_after=5)
        else:
            print(f"[HATA] Uptime komutunda beklenmedik hata: {error}") # logger yerine print
            await ctx.send(f"❓ Uptime komutunda bir hata oluştu.")

async def setup(bot: commands.Bot):
    await bot.add_cog(UptimeCog(bot))
    print("✅ Owner/Uptime Cog yüklendi!")