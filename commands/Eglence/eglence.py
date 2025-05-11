import discord
from discord.ext import commands
import random
import asyncio

class EglenceCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # Soğuk espriler
        self.soguk_espriler = [
            "Naber? 😄 **NABER dedim!** Çünkü naber kelimesi 'Ne haber?'den gelir! 😅 Buzzz!",
            "Hangi gezegen kare şeklindedir? **Kareptün!** 🪐 Soğuk mu dediniz?",
            "Deniz neden tuzludur? **Çünkü balıklar çok ağlar!** 🐟 Brrrr!",
            "Kutu kutu pense, elmam naber dese? **Naber naber naber!** 😜 Soğuk değil mi?",
            "Hangi hayvan en yavaş yürür? **Kap-lum-ba-ğa!** 🐢 Çünkü acele etmez!",
        ]
        # Absürt espriler
        self.absurt_espriler = [
            "Domates neden şarkı söyler? **Çünkü ketch-up star olmak ister!** 🎤",
            "Ayakkabı neden hep yorgun? **Çünkü bütün gün koşturuyor!** 👟",
            "Bulutlar niye partiye gitmez? **Çünkü hep yağmur yağdırır!** ☁️",
            "Ekmek neden dans eder? **Çünkü mayalı!** 🥖💃",
            "Bilgisayar neden utangaçtır? **Çünkü herkes ona tıklar!** 🖱️",
        ]
        # Fıkralar
        self.fikralar = [
            "Temel kahvede arkadaşına anlatır: 'Dün rüyamda Amerika'ya gittim!' Arkadaşı: 'E ne yaptın orada?' Temel: 'Naber dedim, naber dediler!' 😄",
            "Küçük çocuk annesine sorar: 'Anne, naber ne demek?' Anne: 'Naber demek, naber demek!' Çocuk: 'Haaa, naber!' 😅",
            "Dede torununa sorar: 'Okul nasıl?' Torun: 'Naber dede, naber!' Dede: 'Bu çocuk hep naber diyor!' 😜",
            "Adam markete gider, kasiyere: 'Naber?' Kasiyer: 'Naber, poşet ister misiniz?' 😎",
            "Fare kediye sorar: 'Naber kedi?' Kedi: 'Naber mi? Şimdi görürsün!' Fare kaçar: 'Naberrr!' 🐭",
        ]
        # Rastgele kelimeler
        self.rastgele_kelimeler = [
            "Patates", "Kaktüs", "Limon", "Pasta", "Robot",
            "Naber", "Karpuz", "Roket", "Pijama", "Zebra",
        ]
        # Dans emojileri
        self.dans_emojileri = [
            "💃", "🕺", "🪩", "🎶", "🎉",
        ]

    # Yardımcı Fonksiyon: Embed oluşturmayı sadeleştirme
    def create_embed(self, title: str, description: str, color: discord.Color, footer: str = None, thumbnail: str = None):
        embed = discord.Embed(title=title, description=description, color=color)
        if footer:
            embed.set_footer(text=footer)
        if thumbnail:
            embed.set_thumbnail(url=thumbnail)
        return embed

    # !zar komutu
    @commands.command(name="zar")
    @commands.cooldown(1, 5.0, commands.BucketType.user)
    async def zar_at(self, ctx: commands.Context, yuz_sayisi: int = 6):
        """Belirtilen sayıda yüzü olan bir zar atar (varsayılan 6)."""
        if yuz_sayisi < 2 or yuz_sayisi > 100:
            embed = self.create_embed(
                title="❌ Hata!",
                description="Zarın en az 2, en fazla 100 yüzü olmalı! 🎲",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return

        await ctx.send("🎲 Zar atılıyor...")
        await asyncio.sleep(1)
        sonuc = random.randint(1, yuz_sayisi)

        embed = self.create_embed(
            title="🎲 Zar Atıldı!",
            description=f"{ctx.author.mention}, {yuz_sayisi} yüzlü zar attın ve sonuç: **{sonuc}**! 🥳",
            color=discord.Color.purple(),
            thumbnail="https://i.imgur.com/7XqQZQz.png"
        )
        await ctx.send(embed=embed)

    # !yazitura komutu
    @commands.command(name="yazitura")
    @commands.cooldown(1, 5.0, commands.BucketType.user)
    async def yazi_tura(self, ctx: commands.Context):
        """Havaya bir bozuk para atar."""
        await ctx.send("🪙 Para havaya atılıyor...")
        await asyncio.sleep(1)
        sonuc = random.choice(["Yazı", "Tura"])
        emoji = "🪙"

        embed = self.create_embed(
            title=f"{emoji} Para Atıldı!",
            description=f"{ctx.author.mention} para attı ve sonuç: **{sonuc}**! 🎉",
            color=discord.Color.gold(),
            thumbnail="https://i.imgur.com/QkZ7m9b.png"
        )
        await ctx.send(embed=embed)

    # !8ball komutu
    @commands.command(name="8ball")
    @commands.cooldown(1, 5.0, commands.BucketType.user)
    async def sekiz_top(self, ctx: commands.Context, *, soru: str = None):
        """Sihirli 8 topuna bir soru sorun."""
        if not soru:
            embed = self.create_embed(
                title="❌ Hata!",
                description="Bir soru sormalısın! 😅 Mesela: `y!8ball naber?`",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return

        cevaplar = [
            "Kesinlikle evet. ✅",
            "Görünüşe göre iyi. 👍",
            "Büyük ihtimalle. 😎",
            "Evet. 😊",
            "İşaretler eveti gösteriyor. 🔮",
            "Şimdi cevaplamak zor, tekrar dene. 🤔",
            "Daha sonra tekrar sor. ⏳",
            "Şimdi söylemesem daha iyi. 😶",
            "Şu an tahmin edemiyorum. 🌫️",
            "Konsantre ol ve tekrar sor. 🧘",
            "Buna güvenme. 🚫",
            "Cevabım hayır. 😕",
            "Kaynaklarım hayır diyor. 📉",
            "Görünüşe göre pek iyi değil. 😬",
            "Çok şüpheli. 🕵️",
        ]
        await ctx.send("🎱 Sihirli 8 topu düşünülüyor...")
        await asyncio.sleep(1)
        cevap = random.choice(cevaplar)

        embed = self.create_embed(
            title="🎱 Sihirli 8 Topu",
            description="",
            color=discord.Color.blue(),
            footer=f"Soran: {ctx.author.display_name}",
            thumbnail="https://i.imgur.com/4zM8zZm.png"
        )
        embed.add_field(name="Soru", value=soru, inline=False)
        embed.add_field(name="Cevap", value=cevap, inline=False)
        await ctx.send(embed=embed)

    # !sogukespri komutu
    @commands.command(name="sogukespri")
    @commands.cooldown(1, 5.0, commands.BucketType.user)
    async def soguk_espri(self, ctx: commands.Context):
        """Buz gibi bir soğuk espri patlatır."""
        await ctx.send("❄️ Soğuk espri geliyor, hazır ol... Brrrr!")
        await asyncio.sleep(1.5)
        espri = random.choice(self.soguk_espriler)

        embed = self.create_embed(
            title="❄️ Buz Gibi Soğuk Espri!",
            description=f"{ctx.author.mention}, işte esprin: **{espri}** 😆",
            color=discord.Color.light_grey(),
            footer="Üşüdün mü? 😄",
            thumbnail="https://i.imgur.com/9fWqQ2v.png"
        )
        await ctx.send(embed=embed)

    # !saka komutu (şaka olarak düzeltildi)
    @commands.command(name="şaka")
    @commands.cooldown(1, 5.0, commands.BucketType.user)
    async def saka(self, ctx: commands.Context):
        """Rastgele bir fıkra anlatır."""
        await ctx.send("😂 Fıkra zamanı! Hazır mısın?")
        await asyncio.sleep(1.5)
        fıkra = random.choice(self.fikralar)

        embed = self.create_embed(
            title="😂 Fıkra Saati!",
            description=f"{ctx.author.mention}, işte fıkran: **{fıkra}** 😄",
            color=discord.Color.green(),
            footer="Güldün mü? 😜",
            thumbnail="https://i.imgur.com/5yM7z9k.png"
        )
        await ctx.send(embed=embed)

    # !tahmin komutu
    @commands.command(name="tahmin")
    @commands.cooldown(1, 30.0, commands.BucketType.user)
    async def tahmin(self, ctx: commands.Context):
        """1-100 arasında bir sayı tutar, sen tahmin et."""
        sayi = random.randint(1, 100)
        deneme_hakki = 5
        await ctx.send(f"🎯 1-100 arasında bir sayı tuttum! {deneme_hakki} hakkın var, hadi tahmin et!")

        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel and m.content.isdigit()

        while deneme_hakki > 0:
            try:
                msg = await self.bot.wait_for("message", check=check, timeout=30.0)
                tahmin = int(msg.content)

                if tahmin < 1 or tahmin > 100:
                    await ctx.send("Lütfen 1-100 arasında bir sayı gir! 😅")
                    continue

                deneme_hakki -= 1
                if tahmin == sayi:
                    embed = self.create_embed(
                        title="🎉 Tebrikler!",
                        description=f"{ctx.author.mention}, doğru tahmin! Sayı **{sayi}** idi! 🥳",
                        color=discord.Color.gold()
                    )
                    await ctx.send(embed=embed)
                    return
                elif tahmin < sayi:
                    await ctx.send(f"⬆️ Daha büyük bir sayı dene! Kalan hak: {deneme_hakki}")
                else:
                    await ctx.send(f"⬇️ Daha küçük bir sayı dene! Kalan hak: {deneme_hakki}")

                if deneme_hakki == 0:
                    embed = self.create_embed(
                        title="😔 Hakların Bitti!",
                        description=f"{ctx.author.mention}, sayı **{sayi}** idi. Bir dahaki sefere! 😊",
                        color=discord.Color.red()
                    )
                    await ctx.send(embed=embed)
                    return

            except ValueError:
                await ctx.send("Lütfen sadece sayı gir! 😅")
            except asyncio.TimeoutError:
                embed = self.create_embed(
                    title="⏰ Süre Doldu!",
                    description=f"{ctx.author.mention}, süre doldu! Sayı **{sayi}** idi. 😢",
                    color=discord.Color.red()
                )
                await ctx.send(embed=embed)
                return

    # !kedi komutu
    @commands.command(name="kedi")
    @commands.cooldown(1, 5.0, commands.BucketType.user)
    async def kedi(self, ctx: commands.Context):
        """Rastgele kedi emojisi veya sevimli bir mesaj gönderir."""
        kedi_mesajlari = [
            "Miyav miyav! 🐱 Naber?",
            "Bu kedi sana pati atıyor! 😺",
            "Kediler dünyayı yönetir! 🐾",
            "Hadi biraz kedi sev! 😽",
            "Mrrrr... Bu kedi seni sevdi! 🐈",
        ]
        kedi_emojileri = ["🐱", "😺", "🐾", "😽", "🐈"]
        mesaj = random.choice(kedi_mesajlari)
        emoji = random.choice(kedi_emojileri)

        embed = self.create_embed(
            title=f"{emoji} Kedi Zamanı!",
            description=f"{ctx.author.mention}, işte kedin: **{mesaj}** 😻",
            color=discord.Color.orange(),
            footer="Miyav! 😺",
            thumbnail="https://i.imgur.com/8yM7z9k.png"
        )
        await ctx.send(embed=embed)

    # !espripatlat komutu
    @commands.command(name="espripatlat")
    @commands.cooldown(1, 5.0, commands.BucketType.user)
    async def espri_patlat(self, ctx: commands.Context):
        """Absürt ve komik bir espri patlatır."""
        await ctx.send("💥 Espri patlatılıyor... Dikkat!")
        await asyncio.sleep(1.5)
        espri = random.choice(self.absurt_espriler)

        embed = self.create_embed(
            title="💥 Absürt Espri!",
            description=f"{ctx.author.mention}, işte esprin: **{espri}** 😂",
            color=discord.Color.pink(),
            footer="Koptun mu? 😜",
            thumbnail="https://i.imgur.com/5yM7z9k.png"
        )
        await ctx.send(embed=embed)

    # !naber komutu
    @commands.command(name="naber")
    @commands.cooldown(1, 5.0, commands.BucketType.user)
    async def naber(self, ctx: commands.Context):
        """Naber temalı komik bir yanıt verir."""
        naber_yanitlari = [
            "Naberrr! 😄 Benden iyisi yok, sen nasılsın?",
            "Naberrr! 😎 Ben buradayım, sen nerdesin?",
            "Naberrr! 🥳 Parti mi var, niye haber vermedin?",
            "Naberrr! 😺 Kediler miyav dedi, sen ne diyorsun?",
            "Naberrr! 🚀 Uzaya mı gidiyoruz, hazır mısın?",
        ]
        yanit = random.choice(naber_yanitlari)

        embed = self.create_embed(
            title="📣 Nasılsın?",
            description=f"{ctx.author.mention}, {yanit} 🎉",
            color=discord.Color.teal(),
            footer="Nasılsın bakalım? 😊"
        )
        await ctx.send(embed=embed)

    # !rastgele komutu
    @commands.command(name="rastgele")
    @commands.cooldown(1, 5.0, commands.BucketType.user)
    async def rastgele(self, ctx: commands.Context):
        """Rastgele kelimeler ve emojilerle bombardıman yapar."""
        await ctx.send("🎈 Rastgele şeyler geliyor... Hazır ol!")
        await asyncio.sleep(1)
        secilen_kelimeler = random.sample(self.rastgele_kelimeler, 3)  # 3 rastgele kelime
        emojiler = " ".join(random.choices(["🎉", "🌟", "🚀", "🍕", "🐾"], k=3))

        embed = self.create_embed(
            title="🎲 Rastgele Bombardıman!",
            description=f"{ctx.author.mention}, işte rastgele şeyler: **{', '.join(secilen_kelimeler)}** {emojiler}",
            color=discord.Color.random(),
            footer="Rastgele eğlence! 😄"
        )
        await ctx.send(embed=embed)

    # !danset komutu
    @commands.command(name="danset")
    @commands.cooldown(1, 5.0, commands.BucketType.user)
    async def danset(self, ctx: commands.Context):
        """Kullanıcıyı dans etmeye çağırır ve dans emojileri gönderir."""
        await ctx.send("🕺 Dans zamanı! Hadi piste çıkalım! 💃")
        await asyncio.sleep(1)
        dans = " ".join(random.choices(self.dans_emojileri, k=3))

        embed = self.create_embed(
            title="🪩 Dans Pisti Açıldı!",
            description=f"{ctx.author.mention}, hadi dans edelim: {dans} 🎶",
            color=discord.Color.purple(),
            footer="Dans etmeyi bırakma! 🕺"
        )
        await ctx.send(embed=embed)

    # Cooldown hata mesajı
    @commands.Cog.listener()
    async def on_command_error(self, ctx: commands.Context, error):
        if isinstance(error, commands.CommandOnCooldown):
            embed = self.create_embed(
                title="⏳ Yavaşla!",
                description=f"Bu komutu tekrar kullanmak için **{error.retry_after:.1f} saniye** beklemelisin! 😅",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)

async def setup(bot: commands.Bot):
    await bot.add_cog(EglenceCog(bot))
    print("Eglence setup işlemi tamamlandı.")