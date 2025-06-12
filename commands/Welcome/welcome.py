# commands/Welcome/welcome.py
import discord
from discord.ext import commands
# import asyncio # Rol atamada nadiren gerekebilecek gecikme için

class WelcomeCog(commands.Cog, name="Hoş Geldin"):
    """Yeni üyelere hoş geldin mesajı gönderen ve botlara rol atayan Cog."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        if not hasattr(self.bot, 'config') or not self.bot.config:
            print("[HATA] WelcomeCog: Bot yapılandırması (self.bot.config) yüklenmemiş!")

    def get_config_value(self, key: str, default_value=None):
        """Config'den değeri alır, yoksa None veya belirtilen varsayılanı döner."""
        if not hasattr(self.bot, 'config') or not self.bot.config:
            return default_value
        return self.bot.config.get(key, default_value)

    def get_id_from_config(self, key: str, id_type: str = "Öğe") -> int | None:
        """Config'den ID (string) alır ve integer'a çevirir, hata/eksiklik durumunda None döner."""
        item_id_str = self.get_config_value(key)

        if not item_id_str:
            return None
        
        if not isinstance(item_id_str, str):
            print(f"[UYARI] Yapılandırmada '{key}' için beklenen string ID yerine '{type(item_id_str)}' tipi bulundu. Değer: '{item_id_str}'.")
            return None

        try:
            return int(item_id_str)
        except ValueError:
            print(f"[HATA] Yapılandırmadaki '{key}' ('{item_id_str}') geçerli bir sayısal ID değil ({id_type} ID'si için).")
            return None

    async def assign_bot_role(self, member: discord.Member):
        bot_role_id = self.get_id_from_config("BOT_ROLE_ID", "Bot Rolü")
        if not bot_role_id:
            return

        bot_role = member.guild.get_role(bot_role_id)
        if not bot_role:
            print(f"[HATA] Config'de belirtilen BOT_ROLE_ID ('{bot_role_id}') '{member.guild.name}' sunucusunda bulunamadı.")
            return

        try:
            await member.add_roles(bot_role, reason="Sunucuya katılan bota otomatik rol atandı.")
            print(f"[BAŞARI] '{member.display_name}' ({member.id}) adlı bota '{bot_role.name}' rolü verildi.")
        except discord.Forbidden:
            print(f"[HATA] '{member.display_name}' adlı bota '{bot_role.name}' rolü verilemedi. İzinler yetersiz veya rol hiyerarşisi sorunu.")
        except discord.HTTPException as e:
            print(f"[HATA] '{member.display_name}' adlı bota rol verilirken HTTP hatası oluştu: {e}")
        except Exception as e:
            print(f"[HATA] Bot rolü verilirken beklenmedik bir hata oluştu ({member.display_name}): {e}")

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        if not hasattr(self.bot, 'config') or not self.bot.config:
            print("[HATA] WelcomeCog (on_member_join): Bot yapılandırması yüklenmemiş. İşlem yapılamıyor.")
            return

        if member.bot:
            print(f"[BİLGİ] Bir bot katıldı: {member.display_name} ({member.id}). Hoş geldin mesajı gönderilmeyecek.")
            await self.assign_bot_role(member)
            return

        welcome_channel_id = self.get_id_from_config("WELCOME_CHANNEL_ID", "Hoş Geldin Kanalı")
        if not welcome_channel_id:
            print("[BİLGİ] WELCOME_CHANNEL_ID yapılandırılmamış, hoş geldin mesajı gönderilmeyecek.")
            return

        kanal = self.bot.get_channel(welcome_channel_id)
        if not kanal:
            print(f"[HATA] Hoş geldin kanalı (ID: {welcome_channel_id}) bulunamadı veya botun erişimi yok.")
            return
        
        if not isinstance(kanal, discord.TextChannel):
            print(f"[HATA] Hoş geldin kanalı (ID: {welcome_channel_id}) bir metin kanalı değil. Kanal Tipi: {type(kanal)}")
            return

        sunucu = member.guild
        uye_sayisi = sunucu.member_count

        welcome_role_id = self.get_id_from_config("WELCOME_ROLE_ID", "Karşılama Rolü")
        role_ping_text = ""
        if welcome_role_id:
            role_ping_text = f"<@&{welcome_role_id}> "

        # --- İstenen Embed Tasarımı (SADECE GİRİŞ METNİ VE KANAL ID) ---

        def get_channel_mention_or_default(key_name, default_text_if_no_id_in_config="#?"):
            ch_id_str = self.get_config_value(key_name) 
            if ch_id_str and isinstance(ch_id_str, str) and ch_id_str.isdigit():
                return f"<#{ch_id_str}>"
            elif ch_id_str and isinstance(ch_id_str, str) and not ch_id_str.isdigit() and ch_id_str.startswith("#"):
                 return ch_id_str 
            # print(f"[BİLGİ] '{key_name}' için geçerli bir kanal ID'si bulunamadı, varsayılan metin kullanılıyor: '{default_text_if_no_id_in_config}'")
            return default_text_if_no_id_in_config

        rules_ch_mention = get_channel_mention_or_default("RULES_CHANNEL_ID")
        color_role_ch_mention = get_channel_mention_or_default("COLOR_ROLE_CHANNEL_ID")
        general_roles_ch_mention = get_channel_mention_or_default("GENERAL_ROLES_CHANNEL_ID")
        events_ch_mention = get_channel_mention_or_default("EVENTS_CHANNEL_ID")
        giveaways_ch_mention = get_channel_mention_or_default("GIVEAWAYS_CHANNEL_ID")
        partnership_rules_ch_mention = get_channel_mention_or_default("PARTNERSHIP_RULES_CHANNEL_ID")

        embed_description = (
            f"Hoş geldin! Kuralları okumayı unutma {rules_ch_mention}\n"
            f"Kendine bir renk rolü al {color_role_ch_mention}\n"
            f"Rollerimizden uygun olanları almayı unutma {general_roles_ch_mention}\n"
            f"Etkinliklerimize göz at, belki eğlenirsin {events_ch_mention}\n"
            f"Çekilişlerimize katılmayı unutma {giveaways_ch_mention}\n"
            f"Partnerlik şartlarını oku {partnership_rules_ch_mention}"
        )
        # --- Embed Tasarımı Sonu ---
        
        embed_color_hex = self.get_config_value("WELCOME_EMBED_COLOR", "0xFF0000")
        embed_color = discord.Color.red() 
        if isinstance(embed_color_hex, str) and embed_color_hex.startswith("0x"):
            try:
                embed_color = discord.Color(int(embed_color_hex, 16))
            except ValueError:
                print(f"[UYARI] Config'deki 'WELCOME_EMBED_COLOR' ('{embed_color_hex}') geçersiz hex. Varsayılan kırmızı kullanılacak.")
        elif embed_color_hex != "0xFF0000":
            print(f"[UYARI] Config'deki 'WELCOME_EMBED_COLOR' ('{embed_color_hex}') '0x' ile başlamıyor. Varsayılan kırmızı kullanılacak.")

        embed = discord.Embed(
            description=embed_description,
            color=embed_color
        )

        embed.set_footer(text=f"👥 Şu anda sunucumuzda toplam {uye_sayisi} üye bulunuyor!")

        welcome_image_url = self.get_config_value("WELCOME_IMAGE_URL", "")
        if welcome_image_url and isinstance(welcome_image_url, str):
            embed.set_image(url=welcome_image_url)

        try:
            content_message = f"{role_ping_text}Heyy {member.mention}! Yooo! Sen Hoş geldin!"
            await kanal.send(content=content_message.strip(), embed=embed)
        except discord.Forbidden:
            print(f"[HATA] '{kanal.name}' ({kanal.id}) kanalına hoş geldin mesajı gönderme izni yok.")
        except discord.HTTPException as e:
            print(f"[HATA] Hoş geldin mesajı gönderilirken HTTP hatası oluştu: {e}")
        except Exception as e:
            print(f"[HATA] Hoş geldin mesajı gönderilirken beklenmedik bir hata oluştu: {e}")

async def setup(bot: commands.Bot):
    if not hasattr(bot, 'config') or not bot.config:
        print("❌ Welcome Cog yüklenemedi: Bot yapılandırması (bot.config) bulunamadı veya boş.")
        return

    if not bot.config.get("WELCOME_CHANNEL_ID"):
        print("⚠️ Welcome Cog: 'WELCOME_CHANNEL_ID' yapılandırmada bulunamadı. Cog bazı işlevleri yerine getiremeyebilir.")

    await bot.add_cog(WelcomeCog(bot))
