# commands/Owner/shutdown.py
import discord
from discord.ext import commands
# import asyncio # bot.close() için gerekli değil, discord.py hallediyor

class ShutdownCog(commands.Cog, name="Kapatma"): # Yardım komutunun tanıması için Cog adı
    """Botu güvenli bir şekilde kapatma komutunu içerir."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="kapat", aliases=["shutdown"])
    @commands.is_owner() # Sadece bot sahibi kullanabilir
    async def shutdown_command(self, ctx: commands.Context): # Komut adı sınıf adıyla karışmasın diye değiştirdim
        """Botu güvenli bir şekilde kapatır (Sadece sahip kullanabilir)."""
        try:
            await ctx.message.add_reaction("🛑") # Kapatma emojisi
            await ctx.send("Bot kapatılıyor... Hoşçakal!")
            print(f"Bot kapatma komutu {ctx.author} tarafından kullanıldı.") # logger yerine print
            # Botu güvenli bir şekilde kapat
            await self.bot.close()
        except discord.Forbidden:
             # Tepki ekleme izni yoksa mesaj gönderip kapat
             await ctx.send("Bot kapatılıyor...")
             print(f"Bot kapatma komutu {ctx.author} tarafından kullanıldı (tepki izni yok).") # logger yerine print
             await self.bot.close()
        except Exception as e:
            await ctx.send(f"Kapatma sırasında bir hata oluştu: {e}")
            print(f"[HATA] Kapatma hatası: {e}") # logger yerine print

    # Komut hatası yakalama
    @shutdown_command.error
    async def shutdown_error(self, ctx: commands.Context, error):
         if isinstance(error, commands.NotOwner):
            await ctx.send("❌ Bu komutu sadece bot sahibi kullanabilir!")
         else:
             print(f"[HATA] 'kapat' komutunda beklenmedik hata: {error}") # logger yerine print

async def setup(bot: commands.Bot):
    await bot.add_cog(ShutdownCog(bot))
    print("✅ Owner/Shutdown Cog yüklendi!")