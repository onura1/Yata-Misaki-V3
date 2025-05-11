import discord
from discord.ext import commands, tasks
import sqlite3
import random
import math
import time
import os
import json
import asyncio
import logging
from typing import Dict, List, Tuple, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("leveling.log"),
        logging.StreamHandler()
    ]
)

# Dosya adları ve yapılandırma
DB_NAME = "levels.db"
CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "leveling_config.json")
DEFAULT_CONFIG = {
    "xp_range": {"min": 15, "max": 25},
    "xp_cooldown_seconds": 60,
    "level_roles": {},
    "remove_roles_if_below_rank": None,
    "remove_previous_roles": True,
    "blacklisted_channels": [],
    "xp_boosts": {}
}

class LevelingCog(commands.Cog, name="Seviye Sistemi"):
    """Geliştirilmiş XP, Seviye, Seviye Rolleri ve Admin Komutları Sistemi."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.user_message_cooldowns: Dict[int, Dict[int, float]] = {}
        self.conn: Optional[sqlite3.Connection] = None
        self.cursor: Optional[sqlite3.Cursor] = None
        self.config: Dict = DEFAULT_CONFIG.copy()
        self.rank_removal_threshold: Optional[int] = None
        self.logger = logging.getLogger("LevelingCog")
        self._load_config()
        self._init_db()
        # Schedule role correction after bot is ready
        self.bot.loop.create_task(self._correct_level_roles_on_startup())

    # --- Configuration Management ---
    def _load_config(self):
        """Load the configuration from the JSON file."""
        self.logger.info(f"Yapılandırma dosyası yükleniyor: {CONFIG_FILE}")
        try:
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    loaded_config = json.load(f)
                    self.logger.info(f"Yüklenen yapılandırma: {loaded_config}")
                    if not isinstance(loaded_config, dict):
                        raise ValueError("Yapılandırma dosyası bir JSON nesnesi olmalı.")
                    self.config.update(loaded_config)
                    self.logger.info(f"Seviye yapılandırması '{CONFIG_FILE}' başarıyla yüklendi.")
                    self.logger.info(f"Yüklenen level_roles: {self.config.get('level_roles', 'Bulunamadı')}")
            else:
                with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                    json.dump(self.config, f, indent=4)
                self.logger.info(f"Seviye yapılandırması oluşturuldu: '{CONFIG_FILE}'")

            threshold = self.config.get("remove_roles_if_below_rank")
            if threshold is not None:
                try:
                    self.rank_removal_threshold = int(threshold)
                    if self.rank_removal_threshold <= 0:
                        self.rank_removal_threshold = None
                    else:
                        self.logger.info(f"Rank > {self.rank_removal_threshold} ise roller kaldırılacak.")
                except (ValueError, TypeError):
                    self.logger.warning(f"'remove_roles_if_below_rank' değeri geçersiz: '{threshold}'")
                    self.rank_removal_threshold = None
        except json.JSONDecodeError as e:
            self.logger.error(f"Yapılandırma dosyası JSON formatı hatalı: {e}. Varsayılan yapılandırma kullanılıyor.")
            self.config = DEFAULT_CONFIG.copy()
            self._save_config() # Hata durumunda varsayılanı kaydet
            self.rank_removal_threshold = None
        except Exception as e:
            self.logger.error(f"Yapılandırma yüklenirken hata: {e}. Varsayılan yapılandırma kullanılıyor.")
            self.config = DEFAULT_CONFIG.copy()
            self._save_config() # Hata durumunda varsayılanı kaydet
            self.rank_removal_threshold = None


    def _save_config(self):
        """Save the current configuration to the JSON file."""
        try:
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=4)
            self.logger.info(f"Yapılandırma '{CONFIG_FILE}' dosyasına kaydedildi.")
        except Exception as e:
            self.logger.error(f"Yapılandırma kaydedilirken hata: {e}")

    # --- Database Management ---
    def _init_db(self):
        """Initialize the SQLite database with necessary tables and indexes."""
        try:
            self.conn = sqlite3.connect(DB_NAME)
            self.cursor = self.conn.cursor()
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER NOT NULL,
                    guild_id INTEGER NOT NULL,
                    level INTEGER DEFAULT 0,
                    xp INTEGER DEFAULT 0,
                    total_xp INTEGER DEFAULT 0,
                    PRIMARY KEY (user_id, guild_id)
                )
            """)
            try:
                self.cursor.execute("ALTER TABLE users ADD COLUMN total_xp INTEGER DEFAULT 0")
                self.logger.info("DB'ye 'total_xp' sütunu eklendi.")
            except sqlite3.OperationalError: # Sütun zaten varsa bu hata alınır, sorun değil.
                pass
            self.cursor.execute("CREATE INDEX IF NOT EXISTS idx_total_xp ON users (guild_id, total_xp DESC)")
            self.conn.commit()
            self.logger.info(f"'{DB_NAME}' veritabanına bağlandı.")
        except Exception as e:
            self.logger.error(f"Veritabanı başlatma hatası: {e}")
            self.conn = None
            self.cursor = None

    def _get_user_data(self, guild_id: int, user_id: int) -> Tuple[int, int, int]:
        """Retrieve (level, xp, total_xp) for a user. Initialize if not found."""
        if not self.conn or not self.cursor:
            self.logger.error("Veritabanı bağlantısı yok, kullanıcı verisi alınamıyor.")
            return (0, 0, 0)
        try:
            self.cursor.execute(
                "SELECT level, xp, total_xp FROM users WHERE user_id = ? AND guild_id = ?",
                (user_id, guild_id)
            )
            result = self.cursor.fetchone()
            if result and None not in result: # Veritabanından gelen değerlerin None olmadığını kontrol et
                return (int(result[0]), int(result[1]), int(result[2]))
            else:
                # Kullanıcı bulunamadı veya veriler eksik, yeni kayıt oluştur veya sıfırla
                self.logger.info(f"Kullanıcı DB'de bulunamadı/eksik, sıfırlanıyor (K:{user_id}, S:{guild_id})")
                self.cursor.execute(
                    "INSERT OR REPLACE INTO users (user_id, guild_id, level, xp, total_xp) VALUES (?, ?, 0, 0, 0)",
                    (user_id, guild_id)
                )
                self.conn.commit()
                return (0, 0, 0)
        except sqlite3.Error as e:
            self.logger.error(f"Veri alma hatası (K:{user_id}, S:{guild_id}): {e}")
            return (0, 0, 0)

    def _update_user_xp(self, guild_id: int, user_id: int, level: int, xp: int, total_xp: int):
        """Update a user's level, xp, and total_xp in the database."""
        if not self.conn or not self.cursor:
            self.logger.error("Veritabanı bağlantısı yok, XP güncellenemiyor.")
            return
        try:
            self.cursor.execute(
                "INSERT OR REPLACE INTO users (user_id, guild_id, level, xp, total_xp) VALUES (?, ?, ?, ?, ?)",
                (user_id, guild_id, int(level), int(xp), int(total_xp))
            )
            self.conn.commit()
            self.logger.debug(f"Kullanıcı XP güncellendi: K:{user_id}, S:{guild_id}, Seviye:{level}, XP:{xp}, Toplam XP:{total_xp}")
        except sqlite3.Error as e:
            self.logger.error(f"Veri güncelleme hatası (K:{user_id}, S:{guild_id}): {e}")

    # --- Utility Functions ---
    def _calculate_xp_for_level(self, level: int) -> int:
        """Calculate the XP required to reach the next level."""
        if level < 0:
            return 0 # Negatif seviyeler için XP ihtiyacı 0 olsun.
        return 5 * (level ** 2) + (50 * level) + 100

    def _get_user_rank(self, guild_id: int, user_id: int) -> int:
        """Get the user's rank in the guild based on total_xp."""
        if not self.conn or not self.cursor:
            self.logger.error("Veritabanı bağlantısı yok, sıralama alınamıyor.")
            return 0
        try:
            self.cursor.execute(
                "SELECT user_id FROM users WHERE guild_id = ? AND total_xp > 0 ORDER BY total_xp DESC",
                (guild_id,)
            )
            results = self.cursor.fetchall()
            for rank, (uid,) in enumerate(results, start=1):
                if uid == user_id:
                    return rank
            return 0 # Kullanıcı listede yoksa (örneğin hiç XP'si yoksa)
        except sqlite3.Error as e:
            self.logger.error(f"Sıralama alma hatası (S:{guild_id}): {e}")
            return 0

    def _recalculate_level(self, total_xp: int) -> Tuple[int, int]:
        """Recalculate level and current XP based on total XP."""
        level = 0
        xp_cumulative = 0
        xp_needed_for_next = self._calculate_xp_for_level(level)
        while xp_cumulative + xp_needed_for_next <= total_xp:
            xp_cumulative += xp_needed_for_next
            level += 1
            xp_needed_for_next = self._calculate_xp_for_level(level)
        xp_in_level = total_xp - xp_cumulative
        return level, xp_in_level

    def _get_xp_boost(self, member: discord.Member) -> float:
        """Calculate the XP boost multiplier for a member."""
        if "xp_boosts" not in self.config:
            return 1.0
        boost = 1.0
        boosts = self.config["xp_boosts"]
        user_boost = boosts.get(str(member.id)) # ID'ler string olarak saklanmış olabilir
        if user_boost:
            boost = max(boost, float(user_boost))
        for role in member.roles:
            role_boost = boosts.get(str(role.id)) # ID'ler string olarak saklanmış olabilir
            if role_boost:
                boost = max(boost, float(role_boost))
        return boost

    # --- Role Management ---
    async def _update_level_roles(self, member: discord.Member, guild: discord.Guild, new_level: int):
        """Update level-based roles for a member."""
        self.logger.info(f"Rol güncelleme başlatıldı: {member.display_name} (ID: {member.id}), Seviye: {new_level}")
        bot_member = guild.me
        if not bot_member.guild_permissions.manage_roles:
            self.logger.error("Botun 'Rolleri Yönet' izni yok, roller güncellenemez!")
            return

        if "level_roles" not in self.config:
            self.logger.warning("Yapılandırmada 'level_roles' bulunamadı.")
            return

        level_roles_map = self.config["level_roles"]
        self.logger.info(f"Level roles map: {level_roles_map}")

        level_str = str(new_level) # Seviyeler config'de string key olarak tutuluyor
        if level_str not in level_roles_map:
            self.logger.info(f"Seviye {new_level} için rol tanımlı değil.")
            # Eğer önceki rolleri kaldırma aktifse ve bu seviye için rol yoksa,
            # yine de önceki seviye rollerini kaldırmayı düşünebiliriz.
            # Ancak mevcut mantık sadece tanımlı rol varsa işlem yapıyor.
            # İsteğe bağlı olarak burası genişletilebilir.
            if self.config.get("remove_previous_roles", True):
                 # Sadece mevcut seviye için rol tanımlı değilse ama önceki roller kaldırılmalıysa
                roles_to_remove_if_no_new_role = []
                current_role_ids = {role.id for role in member.roles}
                for lvl, role_id_str_iter in level_roles_map.items():
                    try:
                        role_id_int_iter = int(role_id_str_iter)
                        if role_id_int_iter in current_role_ids:
                            role_to_remove_obj = guild.get_role(role_id_int_iter)
                            if role_to_remove_obj and role_to_remove_obj.position < bot_member.top_role.position:
                                roles_to_remove_if_no_new_role.append(role_to_remove_obj)
                    except ValueError:
                        continue # Geçersiz rol ID'sini atla
                if roles_to_remove_if_no_new_role:
                    try:
                        await member.remove_roles(*roles_to_remove_if_no_new_role, reason="Yeni seviye için rol tanımlı değil, eskiler kaldırıldı.")
                        self.logger.info(f"{member.display_name}'dan roller kaldırıldı (yeni seviye için rol yok): {[r.name for r in roles_to_remove_if_no_new_role]}")
                    except discord.Forbidden:
                        self.logger.error(f"{member.display_name} rolleri kaldırılamadı (yeni seviye için rol yok).")
                    except Exception as e:
                        self.logger.error(f"Rol kaldırılırken hata (yeni seviye için rol yok): {e}")
            return


        role_id_to_add_str = level_roles_map[level_str]
        self.logger.info(f"Seviye {new_level} için rol ID: {role_id_to_add_str}")

        try:
            role_to_add_id = int(role_id_to_add_str)
            role_to_add = guild.get_role(role_to_add_id)
            if not role_to_add:
                self.logger.error(f"Seviye {new_level} rol ID({role_to_add_id}) bulunamadı!")
                return
            self.logger.info(f"Rol bulundu: {role_to_add.name} (ID: {role_to_add_id})")

            if role_to_add.position >= bot_member.top_role.position:
                self.logger.error(
                    f"Rol {role_to_add.name} (ID: {role_to_add_id}) botun en yüksek rolünden yüksek veya eşit, rol atanamaz!"
                )
                return

            roles_to_remove = []
            if self.config.get("remove_previous_roles", True):
                current_role_ids = {role.id for role in member.roles}
                self.logger.info(f"Kullanıcının mevcut rolleri: {current_role_ids}")
                for lvl, role_id_str_iter in level_roles_map.items(): # level_roles_map'teki tüm tanımlı rolleri kontrol et
                    try:
                        lvl_int = int(lvl)
                        role_id_int_iter = int(role_id_str_iter)
                        # Sadece farklı seviyelerin rollerini ve eklenecek rol olmayanları kaldır
                        if lvl_int != new_level and role_id_int_iter in current_role_ids and role_id_int_iter != role_to_add_id:
                            role_to_remove_obj = guild.get_role(role_id_int_iter)
                            if role_to_remove_obj:
                                if role_to_remove_obj.position >= bot_member.top_role.position:
                                    self.logger.warning(
                                        f"Rol {role_to_remove_obj.name} (ID: {role_id_int_iter}) botun en yüksek rolünden yüksek, kaldırılamaz!"
                                    )
                                    continue
                                roles_to_remove.append(role_to_remove_obj)
                                self.logger.info(f"Kaldırılacak rol: {role_to_remove_obj.name} (ID: {role_id_int_iter})")
                    except ValueError:
                        self.logger.error(f"Geçersiz seviye veya rol ID: Seviye {lvl}, Rol ID {role_id_str_iter}")
                        continue

            try:
                if roles_to_remove:
                    self.logger.info(f"Roller kaldırılıyor: {[role.name for role in roles_to_remove]}")
                    await member.remove_roles(*roles_to_remove, reason=f"{new_level}. seviye rolü için eskiler kaldırıldı")
                if role_to_add not in member.roles:
                    self.logger.info(f"Rol ekleniyor: {role_to_add.name} (ID: {role_to_add.id})")
                    await member.add_roles(role_to_add, reason=f"Seviye {new_level} ulaştı")
                else:
                    self.logger.info(f"Kullanıcı zaten {role_to_add.name} rolüne sahip.")
            except discord.Forbidden:
                self.logger.error(f"{member.display_name} rolleri güncellenemedi ('Rolleri Yönet' izni eksik veya rol hiyerarşisi sorunu?)")
            except Exception as e:
                self.logger.error(f"Rol güncellenirken hata: {e}")

        except ValueError:
            self.logger.error(f"Seviye {new_level} için rol ID('{role_id_to_add_str}') sayı değil.")
        except Exception as e:
            self.logger.error(f"_update_level_roles içinde beklenmedik hata: {e}")


    async def _remove_all_level_roles(self, member: discord.Member, guild: discord.Guild):
        """Remove all level roles from a member."""
        self.logger.info(f"Tüm seviye rolleri kaldırılıyor: {member.display_name} (ID: {member.id})")
        if "level_roles" not in self.config:
            self.logger.warning("Yapılandırmada 'level_roles' bulunamadı.")
            return

        level_role_map = self.config["level_roles"]
        roles_to_remove = []
        member_role_ids = {role.id for role in member.roles}
        bot_member = guild.me

        for role_id_str in level_role_map.values(): # Sadece config'de tanımlı seviye rollerini kontrol et
            try:
                role_id_int = int(role_id_str)
                if role_id_int in member_role_ids:
                    role_obj = guild.get_role(role_id_int)
                    if role_obj:
                        if role_obj.position >= bot_member.top_role.position: # Düzeltildi: LIFECYCLE kaldırıldı
                            self.logger.warning(
                                f"Rol {role_obj.name} (ID: {role_id_int}) botun en yüksek rolünden yüksek, kaldırılamaz!"
                            )
                            continue
                        roles_to_remove.append(role_obj)
            except ValueError:
                self.logger.error(f"Kaldırma için JSON'daki ID('{role_id_str}') geçersiz.")
                continue

        if roles_to_remove:
            try:
                await member.remove_roles(*roles_to_remove, reason="Seviye sıfırlandı veya sıralama düştü veya rol düzeltmesi")
                self.logger.info(f"{member.display_name}'dan roller kaldırıldı: {[r.name for r in roles_to_remove]}")
            except discord.Forbidden:
                self.logger.error(f"{member.display_name} rolleri kaldırıLAMADI ('Rolleri Yönet' izni eksik veya rol hiyerarşisi sorunu?)")
            except Exception as e:
                self.logger.error(f"Rol kaldırılırken hata: {e}")

    # --- New Role Correction Logic ---
    async def _correct_level_roles_on_startup(self):
        """Correct level roles for all members when the bot starts."""
        await self.bot.wait_until_ready()
        self.logger.info("Bot başlatıldı, seviye rolleri düzeltme işlemi başlıyor.")
        for guild in self.bot.guilds:
            self.logger.info(f"Sunucu: {guild.name} (ID: {guild.id}) için roller kontrol ediliyor.")
            bot_member = guild.me
            if not bot_member.guild_permissions.manage_roles:
                self.logger.error(f"{guild.name} sunucusunda 'Rolleri Yönet' izni yok, düzeltme yapılamaz!")
                continue

            # Üyeleri toplu çekmek yerine iterasyonla almak daha güvenli olabilir
            # özellikle çok büyük sunucularda hafıza sorunlarını önlemek için.
            # fetch_members limit=None potansiyel olarak çok fazla veri çekebilir.
            # Ancak mevcut kodunuzda bu şekilde bırakıyorum.
            async for member in guild.fetch_members(limit=None):
                if member.bot:
                    continue
                await self._correct_member_level_roles(member, guild)
                await asyncio.sleep(0.1)  # Rate limit prevention
        self.logger.info("Seviye rolleri düzeltme işlemi tamamlandı.")

    async def _correct_member_level_roles(self, member: discord.Member, guild: discord.Guild):
        """Correct level roles for a single member."""
        self.logger.info(f"Rol düzeltme: {member.display_name} (ID: {member.id})")
        level, _, _ = self._get_user_data(guild.id, member.id)
        level_roles_map = self.config.get("level_roles", {})
        level_str = str(level) # Seviyeler config'de string key olarak tutuluyor
        bot_member = guild.me

        # Önce TÜM tanımlı seviye rollerini kaldır
        # Bu, kullanıcının sahip olmaması gereken eski seviye rollerini temizler.
        await self._remove_all_level_roles(member, guild)

        # Sonra doğru seviye rolünü ekle (eğer varsa)
        if level_str in level_roles_map:
            try:
                role_id = int(level_roles_map[level_str])
                role = guild.get_role(role_id)
                if not role:
                    self.logger.error(f"Seviye {level} için rol ID({role_id}) bulunamadı!")
                    return
                if role.position >= bot_member.top_role.position:
                    self.logger.error(
                        f"Rol {role.name} (ID: {role_id}) botun en yüksek rolünden yüksek, atanamaz!"
                    )
                    return

                if role not in member.roles: # Zaten sahip değilse ekle
                    await member.add_roles(role, reason=f"Seviye {level} düzeltmesi")
                    self.logger.info(f"{member.display_name} için rol atandı: {role.name} (ID: {role_id})")
                else:
                    self.logger.info(f"{member.display_name} zaten {role.name} rolüne sahip (düzeltme sonrası).")
            except ValueError:
                self.logger.error(f"Seviye {level} için geçersiz rol ID: {level_roles_map[level_str]}")
            except discord.Forbidden:
                self.logger.error(f"{member.display_name} için rol atanamadı ('Rolleri Yönet' izni eksik?)")
            except Exception as e:
                self.logger.error(f"Rol düzeltme hatası (_correct_member_level_roles): {e}")
        else:
            self.logger.info(f"{member.display_name} (Seviye {level}) için atanacak rol bulunamadı (düzeltme).")


    # --- XP Management ---
    async def _grant_xp(self, member: discord.Member, guild: discord.Guild, xp_change: int) -> Tuple[bool, int, int]:
        """Grant or remove XP, update levels and roles."""
        if not self.conn or not self.cursor:
            self.logger.error("Veritabanı bağlantısı yok, XP güncellenemiyor.")
            return (False, 0, 0) # (leveled_up, new_level, old_level)

        guild_id = guild.id
        user_id = member.id
        old_level, old_xp, old_total_xp = self._get_user_data(guild_id, user_id)
        self.logger.info(f"Eski durum: {member.display_name} | Seviye: {old_level}, XP: {old_xp}, Toplam XP: {old_total_xp}")

        new_total_xp = max(0, old_total_xp + xp_change) # XP'nin 0'ın altına düşmemesini sağla
        new_level, new_xp = self._recalculate_level(new_total_xp)

        leveled_up = new_level > old_level
        de_leveled = new_level < old_level

        self._update_user_xp(guild_id, user_id, new_level, new_xp, new_total_xp)
        self.logger.info(
            f"XP Değişimi: {member.display_name} | Değişim: {xp_change:+d} | "
            f"Yeni Toplam XP: {new_total_xp} | Seviye: {old_level} -> {new_level}" # Düzeltildi: "Yeni0>" kaldırıldı
        )

        if leveled_up:
            self.logger.info(f"Seviye atlandı: {old_level} -> {new_level}, rol güncelleme çağrılıyor.")
            await self._update_level_roles(member, guild, new_level)
        elif de_leveled:
            self.logger.info(f"Seviye düşürüldü: {old_level} -> {new_level}, roller güncelleniyor/kaldırılıyor.")
            # Seviye düşünce, ya yeni seviyenin rolü verilmeli ya da tüm seviye rolleri kaldırılmalı.
            # _update_level_roles bunu zaten handle etmeli (yeni seviye için rol varsa verir, yoksa öncekileri kaldırır)
            await self._update_level_roles(member, guild, new_level)


        # Sıralama kontrolü ile rol kaldırma
        if self.rank_removal_threshold is not None:
            current_rank = self._get_user_rank(guild_id, user_id)
            if current_rank > 0 and current_rank > self.rank_removal_threshold:
                self.logger.info(f"Kullanıcı sıralaması ({current_rank}) eşiği geçti ({self.rank_removal_threshold}), tüm seviye rolleri kaldırılıyor.")
                await self._remove_all_level_roles(member, guild) # Bu, mevcut seviye rolünü de kaldırır.

        return leveled_up, new_level, old_level

    # --- Event Listeners ---
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """Grant XP when a user sends a message."""
        if message.author.bot or not message.guild:
            return

        if message.channel.id in self.config.get("blacklisted_channels", []):
            self.logger.debug(f"Kanal {message.channel.id} ({message.channel.name}) engelli, XP verilmeyecek.")
            return

        # Bot prefix'ini dinamik olarak al
        # Bu satırın çalışması için bot objesinin config'inde PREFIX anahtarı olmalı.
        # Eğer bot.command_prefix kullanılıyorsa, ona göre düzenlenmeli.
        # Varsayılan olarak '!' kullanıyorum, eğer bot.config yoksa.
        try:
            prefix = self.bot.config.get("PREFIX", "!") # Veya bot.command_prefix
        except AttributeError: # Eğer self.bot.config yoksa
             prefix = await self.bot.get_prefix(message)
             if isinstance(prefix, list): # Birden fazla prefix varsa ilkini al
                 prefix = prefix[0]


        if message.content.startswith(prefix):
            return

        guild_id = message.guild.id
        user_id = message.author.id
        current_time = time.time()

        if guild_id not in self.user_message_cooldowns:
            self.user_message_cooldowns[guild_id] = {}

        last_message_time = self.user_message_cooldowns[guild_id].get(user_id, 0)
        cooldown = self.config.get("xp_cooldown_seconds", 60)

        if current_time - last_message_time < cooldown:
            return

        self.user_message_cooldowns[guild_id][user_id] = current_time
        xp_range = self.config.get("xp_range", {"min": 15, "max": 25})
        base_xp = random.randint(xp_range["min"], xp_range["max"])
        boost = self._get_xp_boost(message.author)
        xp_to_add = int(base_xp * boost)

        self.logger.debug(f"XP veriliyor: {message.author.display_name}, Temel XP: {base_xp}, Çarpan: x{boost:.2f}, Toplam XP: {xp_to_add}")
        leveled_up, new_level, old_level = await self._grant_xp(message.author, message.guild, xp_to_add)

        if leveled_up:
            try:
                await message.channel.send(
                    f"🎉 Tebrikler {message.author.mention}, **{new_level}. seviyeye** ulaştın!"
                )
            except discord.Forbidden:
                self.logger.warning(f"Seviye atlama mesajı gönderilemedi (izin yok): {message.channel.name}")
            except Exception as e:
                self.logger.error(f"Seviye atlama mesajı hatası: {e}")

    # --- User Commands ---
    @commands.command(name="seviye")
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def rank_command(self, ctx: commands.Context, member: discord.Member = None):
        """Display a user's level and XP information."""
        if not ctx.guild:
            await ctx.send("Bu komut sadece sunucularda kullanılabilir.")
            return
        if not self.conn: # Veritabanı bağlantısını kontrol et
            await ctx.send("Veritabanı hatası nedeniyle seviye bilgisi alınamıyor. Lütfen daha sonra tekrar deneyin.")
            self.logger.error("rank_command: Veritabanı bağlantısı yok.")
            return

        target_member = member or ctx.author
        guild_id = ctx.guild.id
        user_id = target_member.id

        level, xp, total_xp = self._get_user_data(guild_id, user_id)
        xp_needed = self._calculate_xp_for_level(level)
        rank = self._get_user_rank(guild_id, user_id)
        boost = self._get_xp_boost(target_member)

        member_roles = [role for role in target_member.roles if role.id != ctx.guild.id] # @everyone rolünü hariç tut
        top_role = max(member_roles, key=lambda r: r.position, default=None) if member_roles else None
        top_role_name = top_role.name if top_role else "Yok"
        embed_color = discord.Color.blue() # Varsayılan renk
        if top_role and top_role.color.value != 0:
            embed_color = top_role.color
        elif target_member.color.value !=0:
            embed_color = target_member.color


        embed = discord.Embed(
            title=f"{target_member.display_name} Seviye Bilgisi",
            color=embed_color
        )
        embed.set_thumbnail(url=target_member.display_avatar.url)
        embed.add_field(name="Seviye", value=f"**{level}**", inline=True)
        embed.add_field(name="XP", value=f"**{xp} / {xp_needed}**", inline=True)
        embed.add_field(name="Sıralama", value=f"**#{rank}**" if rank > 0 else "N/A", inline=True)
        embed.add_field(name="En Yüksek Rol", value=f"{top_role_name}", inline=True)
        embed.add_field(name="XP Çarpanı", value=f"**x{boost:.2f}**", inline=True)

        progress = 0
        if xp_needed > 0 : # 0'a bölme hatasını engelle
            progress = int((xp / xp_needed) * 20) # 20 karakterlik progress bar
        progress = max(0, min(progress, 20)) # Değerin 0-20 arasında kalmasını sağla

        progress_bar = f"[{'=' * progress}{'─' * (20 - progress)}]"
        embed.add_field(name=f"Seviye {level+1} İlerlemesi", value=f"`{progress_bar}`", inline=False)
        embed.set_footer(text=f"Toplam Kazanılan XP: {total_xp}")
        await ctx.send(embed=embed)

    @commands.command(name="lider")
    @commands.cooldown(1, 10, commands.BucketType.guild)
    async def leaderboard_command(self, ctx: commands.Context, page: int = 1):
        """Display the leaderboard with pagination."""
        if not ctx.guild:
            await ctx.send("Bu komut sadece sunucularda kullanılabilir.")
            return
        if not self.conn or not self.cursor:
            await ctx.send("Veritabanı hatası nedeniyle liderlik tablosu alınamıyor.")
            self.logger.error("leaderboard_command: Veritabanı bağlantısı yok.")
            return

        page = max(1, page) # Sayfa numarasının en az 1 olmasını sağla
        per_page = 10
        offset = (page - 1) * per_page
        guild_id = ctx.guild.id

        try:
            # Toplam giriş sayısını al
            self.cursor.execute(
                "SELECT COUNT(*) FROM users WHERE guild_id = ? AND total_xp > 0",
                (guild_id,)
            )
            total_entries_result = self.cursor.fetchone()
            total_entries = total_entries_result[0] if total_entries_result else 0

            if total_entries == 0:
                embed = discord.Embed(
                    title=f"🏆 {ctx.guild.name} Liderlik Tablosu (Toplam XP)",
                    description="Bu sunucuda henüz kimse XP kazanmamış.",
                    color=discord.Color.gold()
                )
                await ctx.send(embed=embed)
                return

            total_pages = max(1, (total_entries + per_page - 1) // per_page) # math.ceil yerine
            page = max(1, min(page, total_pages)) # Sayfanın sınırlar içinde kalmasını sağla
            offset = (page - 1) * per_page # Offset'i yeniden hesapla (eğer page değiştiyse)


            self.cursor.execute(
                "SELECT user_id, level, total_xp FROM users WHERE guild_id = ? AND total_xp > 0 ORDER BY total_xp DESC LIMIT ? OFFSET ?",
                (guild_id, per_page, offset)
            )
            results = self.cursor.fetchall()

            embed = discord.Embed(
                title=f"🏆 {ctx.guild.name} Liderlik Tablosu (Toplam XP)",
                color=discord.Color.gold()
            )

            if not results and page == 1 : # İlk sayfada bile sonuç yoksa (yukarıdaki total_entries kontrolü bunu yakalamalıydı)
                embed.description = "Bu sunucuda henüz kimse XP kazanmamış."
            elif not results:
                 embed.description = "Bu sayfada gösterilecek kullanıcı yok."
            else:
                description = ""
                for rank_num, (user_id, level, total_xp) in enumerate(results, start=offset + 1):
                    member = ctx.guild.get_member(user_id)
                    member_name = member.display_name if member else f"Ayrılmış Üye (ID: {user_id})"
                    description += (
                        f"**{rank_num}.** {member_name} - Seviye: {level} (Toplam XP: {total_xp})\n"
                    )
                embed.description = description

            embed.set_footer(text=f"Sayfa {page}/{total_pages} | Toplam Sıralanan Üye: {total_entries}")
            await ctx.send(embed=embed)

        except Exception as e:
            self.logger.error(f"Liderlik tablosu hatası: {e}")
            await ctx.send("Liderlik tablosu alınırken bir hata oluştu.")

    # --- Admin Commands ---
    @commands.command(name="xpekle", aliases=["addxp"])
    @commands.has_permissions(manage_guild=True)
    @commands.cooldown(1, 2, commands.BucketType.user)
    async def add_xp_command(self, ctx: commands.Context, member: discord.Member, amount: int):
        """Add XP to a member."""
        if amount <= 0:
            await ctx.send("❌ Eklenecek XP miktarı pozitif olmalı.")
            return
        if not self.conn:
            await ctx.send("❌ Veritabanı hatası nedeniyle XP eklenemiyor.")
            return

        _, new_level, _ = await self._grant_xp(member, ctx.guild, amount)
        await ctx.send(f"✅ {member.mention} kullanıcısına **{amount} XP** eklendi. Yeni seviyesi: **{new_level}**.")

    @add_xp_command.error
    async def add_xp_error(self, ctx: commands.Context, error):
        """Error handler for add_xp_command."""
        prefix = ctx.prefix # ctx.prefix zaten string olmalı
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("❌ Bu komutu kullanmak için 'Sunucuyu Yönet' iznine sahip olmalısınız.")
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f"❌ Kullanım: `{prefix}xpekle <@üye> <miktar>` (Örn: `{prefix}xpekle @KullanıcıAdı 100`)")
        elif isinstance(error, commands.MemberNotFound):
            await ctx.send(f"❌ Üye bulunamadı: `{error.argument}`. Lütfen geçerli bir üye etiketleyin.")
        elif isinstance(error, commands.BadArgument): # Miktar için
            await ctx.send("❌ Geçersiz XP miktarı. Lütfen bir sayı girin.")
        elif isinstance(error, commands.CommandOnCooldown):
            await ctx.send(f"⏳ Bu komutu tekrar kullanmak için {error.retry_after:.1f} saniye beklemelisiniz.")
        else:
            self.logger.error(f"xpekle komut hatası: {error} (Tip: {type(error)})")
            await ctx.send("❓ Komut kullanılırken bilinmeyen bir hata oluştu.")


    @commands.command(name="xpsil", aliases=["removexp"])
    @commands.has_permissions(manage_guild=True)
    @commands.cooldown(1, 2, commands.BucketType.user)
    async def remove_xp_command(self, ctx: commands.Context, member: discord.Member, amount: int):
        """Remove XP from a member."""
        if amount <= 0:
            await ctx.send("❌ Silinecek XP miktarı pozitif olmalı.")
            return
        if not self.conn:
            await ctx.send("❌ Veritabanı hatası nedeniyle XP silinemiyor.")
            return

        _, new_level, old_level = await self._grant_xp(member, ctx.guild, -amount) # Negatif değer göndererek XP sil
        await ctx.send(f"✅ {member.mention} kullanıcısından **{amount} XP** silindi. Yeni seviyesi: **{new_level}**.")
        if new_level < old_level:
            await ctx.send(f"📉 {member.mention}, {old_level}. seviyesinden **{new_level}**. seviyesine düştü.")

    @remove_xp_command.error
    async def remove_xp_error(self, ctx: commands.Context, error):
        """Error handler for remove_xp_command."""
        prefix = ctx.prefix
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("❌ Bu komutu kullanmak için 'Sunucuyu Yönet' iznine sahip olmalısınız.")
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f"❌ Kullanım: `{prefix}xpsil <@üye> <miktar>` (Örn: `{prefix}xpsil @KullanıcıAdı 50`)")
        elif isinstance(error, commands.MemberNotFound):
            await ctx.send(f"❌ Üye bulunamadı: `{error.argument}`. Lütfen geçerli bir üye etiketleyin.")
        elif isinstance(error, commands.BadArgument):
            await ctx.send("❌ Geçersiz XP miktarı. Lütfen bir sayı girin.")
        elif isinstance(error, commands.CommandOnCooldown):
            await ctx.send(f"⏳ Bu komutu tekrar kullanmak için {error.retry_after:.1f} saniye beklemelisiniz.")
        else:
            self.logger.error(f"xpsil komut hatası: {error} (Tip: {type(error)})")
            await ctx.send("❓ Komut kullanılırken bilinmeyen bir hata oluştu.")

    @commands.command(name="seviyesifirla", aliases=["resetxp", "levelreset"])
    @commands.has_permissions(manage_guild=True)
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def reset_xp_command(self, ctx: commands.Context, member: discord.Member):
        """Reset a member's XP and level."""
        if not self.conn or not self.cursor: # cursor da kontrol edilmeli
            await ctx.send("❌ Veritabanı hatası nedeniyle seviye sıfırlanamıyor.")
            return

        guild_id = ctx.guild.id
        user_id = member.id
        confirmation_msg = await ctx.send(
            f"⚠️ **Emin misiniz?** {member.mention} kullanıcısının tüm seviye/XP ilerlemesi sıfırlanacak "
            f"ve tüm seviye rolleri kaldırılacaktır. Onaylamak için ✅ (15 saniye).",
            delete_after=20.0 # Mesajın 20 saniye sonra silinmesi
        )
        await confirmation_msg.add_reaction("✅")
        await confirmation_msg.add_reaction("❌")

        def check(reaction, user):
            return user == ctx.author and str(reaction.emoji) in ["✅", "❌"] and reaction.message.id == confirmation_msg.id

        try:
            reaction, user = await self.bot.wait_for('reaction_add', timeout=15.0, check=check)
            if str(reaction.emoji) == "✅":
                try:
                    # Kullanıcının XP'sini ve seviyesini DB'de sıfırla
                    self.cursor.execute(
                        "INSERT OR REPLACE INTO users (user_id, guild_id, level, xp, total_xp) VALUES (?, ?, 0, 0, 0)",
                        (user_id, guild_id)
                    )
                    self.conn.commit()
                    # Kullanıcının tüm seviye rollerini kaldır
                    await self._remove_all_level_roles(member, ctx.guild)
                    await confirmation_msg.edit(content=f"✅ {member.mention} kullanıcısının seviyesi ve XP'si başarıyla sıfırlandı, seviye rolleri kaldırıldı.", delete_after=10.0)
                except Exception as e:
                    self.logger.error(f"Seviye sıfırlama (DB/Rol) hatası: {e}")
                    await confirmation_msg.edit(content="❌ Sıfırlama sırasında bir veritabanı veya rol hatası oluştu.", delete_after=10.0)
            else: # '❌' emojisine tıklandı
                await confirmation_msg.edit(content="❌ İşlem iptal edildi.", delete_after=10.0)
        except asyncio.TimeoutError:
            await confirmation_msg.edit(content="⏰ Onay süresi doldu, işlem iptal edildi!", delete_after=10.0)
        finally:
            try:
                await confirmation_msg.clear_reactions() # Zaman aşımı veya işlem sonrası reaksiyonları temizle
            except discord.Forbidden: # Botun reaksiyonları temizleme izni yoksa
                pass
            except discord.NotFound: # Mesaj zaten silinmişse
                pass


    @reset_xp_command.error
    async def reset_xp_error(self, ctx: commands.Context, error):
        """Error handler for reset_xp_command."""
        prefix = ctx.prefix
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("❌ Bu komutu kullanmak için 'Sunucuyu Yönet' iznine sahip olmalısınız.")
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f"❌ Kullanım: `{prefix}seviyesifirla <@üye>` (Örn: `{prefix}seviyesifirla @KullanıcıAdı`)")
        elif isinstance(error, commands.MemberNotFound):
            await ctx.send(f"❌ Üye bulunamadı: `{error.argument}`. Lütfen geçerli bir üye etiketleyin.")
        elif isinstance(error, commands.CommandOnCooldown):
            await ctx.send(f"⏳ Bu komutu tekrar kullanmak için {error.retry_after:.1f} saniye beklemelisiniz.")
        else:
            self.logger.error(f"seviyesifirla komut hatası: {error} (Tip: {type(error)})")
            await ctx.send("❓ Komut kullanılırken bilinmeyen bir hata oluştu.")


    @commands.command(name="xpayar")
    @commands.has_permissions(manage_guild=True)
    async def set_xp_range(self, ctx: commands.Context, min_xp: int, max_xp: int):
        """Set the XP range for messages."""
        if min_xp <= 0 or max_xp <= 0:
            await ctx.send("❌ XP değerleri pozitif olmalı.")
            return
        if min_xp > max_xp:
            await ctx.send("❌ Minimum XP, maksimum XP'den büyük olamaz.")
            return
        self.config["xp_range"] = {"min": min_xp, "max": max_xp}
        self._save_config()
        await ctx.send(f"✅ Mesaj başına kazanılacak XP aralığı güncellendi: **{min_xp} - {max_xp} XP**.")

    @commands.command(name="kanalengelle")
    @commands.has_permissions(manage_guild=True)
    async def blacklist_channel(self, ctx: commands.Context, channel: discord.TextChannel):
        """Blacklist a channel from XP gain."""
        channel_id = channel.id
        if "blacklisted_channels" not in self.config: # Eğer liste config'de yoksa oluştur
            self.config["blacklisted_channels"] = []

        if channel_id not in self.config["blacklisted_channels"]:
            self.config["blacklisted_channels"].append(channel_id)
            self._save_config()
            await ctx.send(f"✅ {channel.mention} kanalı XP kazanımı için başarıyla engellendi.")
        else:
            await ctx.send(f"ℹ️ {channel.mention} kanalı zaten XP kazanımına engelli.")


    @commands.command(name="kanalac")
    @commands.has_permissions(manage_guild=True)
    async def unblacklist_channel(self, ctx: commands.Context, channel: discord.TextChannel):
        """Remove a channel from the XP blacklist."""
        channel_id = channel.id
        if "blacklisted_channels" in self.config and channel_id in self.config["blacklisted_channels"]:
            self.config["blacklisted_channels"].remove(channel_id)
            self._save_config()
            await ctx.send(f"✅ {channel.mention} kanalının XP kazanım engeli başarıyla kaldırıldı.")
        else:
            await ctx.send(f"ℹ️ {channel.mention} kanalı zaten XP kazanımına engelli değil.")

    @commands.command(name="xpboost")
    @commands.has_permissions(manage_guild=True)
    async def set_xp_boost(self, ctx: commands.Context, target: discord.Member | discord.Role, multiplier: float):
        """Set an XP boost for a user or role."""
        if multiplier <= 0:
            await ctx.send("❌ Çarpan pozitif bir değer olmalı (Örn: 1.5 veya 2).")
            return
        if "xp_boosts" not in self.config: # Eğer dict config'de yoksa oluştur
            self.config["xp_boosts"] = {}

        target_id = str(target.id) # Config dosyasında ID'ler string olarak tutulabilir
        self.config["xp_boosts"][target_id] = multiplier
        self._save_config()
        target_type = "üye" if isinstance(target, discord.Member) else "rol"
        await ctx.send(f"✅ {target.mention} ({target_type}) için XP çarpanı **x{multiplier:.2f}** olarak ayarlandı.")

    @set_xp_boost.error
    async def set_xp_boost_error(self, ctx: commands.Context, error):
        """Error handler for set_xp_boost command."""
        prefix = ctx.prefix
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("❌ Bu komutu kullanmak için 'Sunucuyu Yönet' iznine sahip olmalısınız.")
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f"❌ Kullanım: `{prefix}xpboost <@üye veya @rol> <çarpan>` (Örn: `{prefix}xpboost @YetkiliRolü 1.5`)")
        elif isinstance(error, commands.BadUnionArgument): # Hem Member hem Role için ortak hata
             await ctx.send(f"❌ Geçersiz hedef. Lütfen bir üye (@üye) veya bir rol (@rol) etiketleyin. `{error.param.name}` parametresi için `{error.argument}` değeri geçersiz.")
        elif isinstance(error, commands.BadArgument): # Çarpan için
            await ctx.send("❌ Geçersiz çarpan. Lütfen bir sayı girin (örneğin: 1.5 veya 2).")
        else:
            self.logger.error(f"xpboost komut hatası: {error} (Tip: {type(error)})")
            await ctx.send("❓ Komut kullanılırken bilinmeyen bir hata oluştu.")


    @commands.command(name="xpboostkaldir")
    @commands.has_permissions(manage_guild=True)
    async def remove_xp_boost(self, ctx: commands.Context, target: discord.Member | discord.Role):
        """Remove an XP boost from a user or role."""
        target_id = str(target.id)
        if "xp_boosts" in self.config and target_id in self.config["xp_boosts"]:
            del self.config["xp_boosts"][target_id]
            self._save_config()
            target_type = "üye" if isinstance(target, discord.Member) else "rol"
            await ctx.send(f"✅ {target.mention} ({target_type}) için tanımlanmış XP çarpanı başarıyla kaldırıldı.")
        else:
            await ctx.send(f"ℹ️ {target.mention} için zaten tanımlı bir XP çarpanı bulunmuyor.")

    # --- Cog Lifecycle ---
    def cog_unload(self):
        """Clean up when the cog is unloaded."""
        if self.conn:
            self.conn.close()
            self.logger.info("Cog kaldırıldı, veritabanı bağlantısı kapatıldı.")

async def setup(bot: commands.Bot):
    """Setup function to load the cog."""
    try:
        import sqlite3 # Bu zaten en başta import edilmişti ama burada tekrar kontrol etmek iyi bir pratik.
    except ImportError:
        logging.critical("SQLite3 modülü bulunamadı! Seviye sistemi ÇALIŞMAYACAK. Lütfen `pip install pysqlite3` veya sisteminize uygun sqlite3 paketini kurun.")
        return

    # Veritabanı dosyasının varlığını kontrol et, yoksa uyarı ver. _init_db zaten oluşturacak.
    if not os.path.exists(DB_NAME):
        logging.warning(f"'{DB_NAME}' veritabanı dosyası bulunamadı. İlk XP kazanımında veya bot başlatıldığında oluşturulacaktır.")

    await bot.add_cog(LevelingCog(bot))
    logging.info("Leveling Cog (Seviye Sistemi) başarıyla yüklendi!")
    # Düzeltildi: "hata alıyorum" kısmı kaldırıldı.