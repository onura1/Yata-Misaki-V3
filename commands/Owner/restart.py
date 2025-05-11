# commands/Owner/restart.py
import discord
from discord.ext import commands
import os     # os.execv için
import sys    # sys.executable ve sys.argv için

class RestartCog(commands.Cog, name="Yeniden Başlatma"): # Yardım komutunun tanıması için Cog adı
    """Botu yeniden başlatma komutunu içerir."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="restart", aliases=["reboot", "yenidenbaslat"])
    @commands.is_owner() # Sadece sahip kullanabilir
    async def restart_command(self, ctx: commands.Context): # Komut adı sınıf adıyla karışmasın diye değiştirdim
        """Botu yeniden başlatır (Sadece sahip kullanabilir)."""
        try:
            await ctx.message.add_reaction("🔄")
            await ctx.send("Bot yeniden başlatılıyor...")
            print(f"Bot yeniden başlatma komutu {ctx.author} tarafından kullanıldı.") # logger yerine print
            # Python script'ini yeniden çalıştır
            os.execv(sys.executable, ['python'] + sys.argv)
        except discord.Forbidden:
             await ctx.send("Yeniden başlatılıyor...")
             print(f"Bot yeniden başlatma komutu {ctx.author} tarafından kullanıldı (tepki izni yok).") # logger yerine print
             os.execv(sys.executable, ['python'] + sys.argv)
        except Exception as e:
            await ctx.send(f"Yeniden başlatma sırasında bir hata oluştu: {e}")
            print(f"[HATA] Yeniden başlatma hatası: {e}") # logger yerine print

    # Komut hatası yakalama
    @restart_command.error
    async def restart_error(self, ctx: commands.Context, error):
         if isinstance(error, commands.NotOwner):
            await ctx.send("❌ Bu komutu sadece bot sahibi kullanabilir!")
         else:
            print(f"[HATA] 'restart' komutunda beklenmedik hata: {error}") # logger yerine print

async def setup(bot: commands.Bot):
    await bot.add_cog(RestartCog(bot))
    print("✅ Owner/Restart Cog yüklendi!")