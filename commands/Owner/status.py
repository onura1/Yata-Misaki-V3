# Yata Misaki/commands/status.py

import discord
from discord.ext import commands
# 'typing' modülüne gerek kalmadı (şimdilik)

class StatusCog(commands.Cog, name="Durum Ayarları"):
    """Botun Discord durumunu ve aktivitesini ayarlama komutunu içerir."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="durum")
    @commands.is_owner() # Sadece bot sahibi kullanabilir
    async def set_status(self, ctx: commands.Context, tip: str, discord_durumu: str, *, aktivite: str = ""):
        """
        Botun durumunu ve aktivitesini değiştirir (Sadece sahip kullanabilir).
        Kullanım: y!durum [tip] [discord_durumu] [aktivite metni]

        Tipler        : oynuyor, dinliyor, izliyor, yarısıyor, temizle
        Discord Durumu: online (çevrimiçi), idle (boşta), dnd (rahatsızetme), invisible (görünmez)

        Örnekler:
        y!durum oynuyor dnd Çok önemli işler!
        y!durum dinliyor idle Sakin müzikler
        y!durum izliyor online Seni!
        y!durum temizle online (Sadece durumu online yapar, aktiviteyi siler)
        """
        new_activity = None
        tip = tip.lower() # Küçük harfe çevir
        status_key = discord_durumu.lower() # Küçük harfe çevir

        # Discord Durumunu Ayarla
        status_map = {
            "online": discord.Status.online,
            "çevrimiçi": discord.Status.online,
            "idle": discord.Status.idle,
            "boşta": discord.Status.idle,
            "dnd": discord.Status.dnd,
            "rahatsızetme": discord.Status.dnd,
            "rahatsız": discord.Status.dnd, # Alternatif isim
            "invisible": discord.Status.invisible,
            "görünmez": discord.Status.invisible,
            "offline": discord.Status.invisible # Offline'ı görünmez yapalım
        }

        # Girilen durum geçerli mi kontrol et, değilse hata ver
        selected_status = status_map.get(status_key)
        if selected_status is None:
             await ctx.send(f"❌ Geçersiz Discord durumu: `{discord_durumu}`.\n"
                            f"Kullanılabilir durumlar: `online` (çevrimiçi), `idle` (boşta), `dnd` (rahatsızetme), `invisible` (görünmez)")
             return

        # Aktivite Tipini Ayarla
        if tip == "oynuyor":
            if not aktivite and tip != "temizle": # Temizle değilse aktivite metni zorunlu
                 await ctx.send(f"❓ Lütfen oynadığı aktivitenin adını girin. Kullanım: `{self.bot.config['PREFIX']}durum oynuyor {discord_durumu} [oyun adı]`")
                 return
            new_activity = discord.Game(name=aktivite)
        elif tip == "dinliyor":
            if not aktivite and tip != "temizle":
                 await ctx.send(f"❓ Lütfen dinlediği aktivitenin adını girin. Kullanım: `{self.bot.config['PREFIX']}durum dinliyor {discord_durumu} [şarkı/podcast adı]`")
                 return
            new_activity = discord.Activity(type=discord.ActivityType.listening, name=aktivite)
        elif tip == "izliyor":
            if not aktivite and tip != "temizle":
                 await ctx.send(f"❓ Lütfen izlediği aktivitenin adını girin. Kullanım: `{self.bot.config['PREFIX']}durum izliyor {discord_durumu} [film/video adı]`")
                 return
            new_activity = discord.Activity(type=discord.ActivityType.watching, name=aktivite)
        elif tip == "yarısıyor":
            if not aktivite and tip != "temizle":
                 await ctx.send(f"❓ Lütfen yarıştığı aktivitenin adını girin. Kullanım: `{self.bot.config['PREFIX']}durum yarısıyor {discord_durumu} [yarışma adı]`")
                 return
            new_activity = discord.Activity(type=discord.ActivityType.competing, name=aktivite)
        elif tip == "temizle":
            new_activity = None # Aktiviteyi kaldır
            aktivite = "(Aktivite Temizlendi)" # Loglama için
        else:
            await ctx.send(f"❌ Geçersiz aktivite tipi: `{tip}`.\n"
                           f"Kullanılabilir tipler: `oynuyor`, `dinliyor`, `izliyor`, `yarısıyor`, `temizle`")
            return

        # Değişikliği Uygula
        try:
            await self.bot.change_presence(status=selected_status, activity=new_activity)
            await ctx.message.add_reaction("✅")
            print(f"Bot durumu değiştirildi: Durum={selected_status.name}, Tip={tip}, Aktivite='{aktivite}'")
        except Exception as e:
            await ctx.send(f"Durum değiştirilirken bir hata oluştu: {e}")
            print(f"Durum değiştirme hatası: {e}")

    # Bu komuta özel hata yakalama
    @set_status.error
    async def set_status_error(self, ctx: commands.Context, error):
         if isinstance(error, commands.NotOwner):
            await ctx.send("❌ Bu komutu sadece bot sahibi kullanabilir!")
         elif isinstance(error, commands.MissingRequiredArgument):
             # Eksik argümana göre daha açıklayıcı mesaj verelim
             if error.param.name == 'tip':
                 await ctx.send(f"❌ Aktivite tipini belirtmediniz! (`oynuyor`, `dinliyor` vb.)")
             elif error.param.name == 'discord_durumu':
                  await ctx.send(f"❌ Discord durumunu belirtmediniz! (`online`, `idle`, `dnd`, `invisible`)")
             # Aktivite metni * ile alındığı için genellikle bu hatayı vermez ama yine de ekleyelim
             elif error.param.name == 'aktivite':
                  await ctx.send(f"❌ Aktivite metnini belirtmediniz!")
             else:
                  await ctx.send(f"❌ Eksik argüman! Kullanım: `{self.bot.config['PREFIX']}durum [tip] [discord_durumu] [aktivite metni]`")
         else:
            print(f"'durum' komutunda beklenmedik hata: {error}")
            await ctx.send(f"❓ Durum komutunda bir hata oluştu.")


# Cog'u bota tanıtmak için gerekli setup fonksiyonu
async def setup(bot: commands.Bot):
    await bot.add_cog(StatusCog(bot))
    print("✅ Status Cog (Durum) yüklendi!")