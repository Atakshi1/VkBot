import vk_api
from typing import Optional, List
import time
import random
import json
from vk_api.longpoll import VkLongPoll, VkEventType
from commands import Commands
from funcommands import FunCommands
import logging
import re

TOKEN = "vk1.a.k9_-_02nzLMvn1y7BQA7q833OEnoI0niTdSP_ahN6V1NBs2Bj3FGqacKXZXNqZuMtd4pL06akTVg3f7gVkgmcMTr61kcRrsZ632iUl0c1VBHb7GrOYH0jurG_Vhx1Gu4g_iGz931xb7yNGy4TLUkVcEzYb7ChAFo0FRA9MV38KDlT6CLYij6AePPmdCu0DtLf7HZ_f5R3dRYugpqKI5D0A"

class VKBot:
    def __init__(self):
        self.vk_session = vk_api.VkApi(token=TOKEN)
        self.vk = self.vk_session.get_api()
        self.longpoll = VkLongPoll(self.vk_session)

        # Инициализация команд
        self.commands = Commands(self.vk)
        self.fun_commands = FunCommands(self.vk)

        self.bot_id = self.vk.users.get()[0]['id']
        self.last_members = {}
        self.deletion_cooldowns = {}
        self.last_deletion_info = {}
        self.blocked_chats = set()
        self._muted_chats = set()
        self._last_activity_check = {}
        self._last_mute_check = {}
        self._mute_check_interval = 300
        self._last_api_error = None

        self.owner_id = 191451023
        self.moderators_file = 'moderators.json'
        self.moderators: List[int] = []
        self._init_moderation_system()

        self.auto_responses = self._load_auto_responses()  # Загружаем автоответы
        self.last_command_time = {}  # Храним время последнего ответа на команду

    # Словари для фильтрации (оставляем как есть)
        self.bad_words = [
            'хуй', 'пизда', 'ебал', 'ебать', 'блядь', 'бля', 'гандон', 'мудак',
            'пидор', 'педик', 'мат', 'проститутка', 'сука', 'сучка', 'долбаёб',
            'залупа', 'гондон', 'пиздец', 'еблан', 'выебок', 'выебываться',
            'fuck', 'shit', 'bitch', 'asshole', 'dick', 'pussy', 'cock', 'whore'
        ]

        self.word_replacements = {
            'хуй': 'редиска', 'пизда': 'печенька', 'ебал': 'обнимал', 'ебать': 'целовать',
            'блядь': 'бяка', 'бля': 'блин', 'гандон': 'шарик', 'мудак': 'одуванчик',
            'пидор': 'помидор', 'педик': 'педикюр', 'мат': 'шляпа', 'проститутка': 'профессионалка',
            'сука': 'сушка', 'сучка': 'сушечка', 'долбаёб': 'милашка', 'залупа': 'заколка',
            'гондон': 'гонщик', 'пиздец': 'песец', 'еблан': 'обалдуй', 'выебок': 'выпендрёж',
            'выебываться': 'выделываться'
        }

    def edit_message(self, peer_id, message_id, new_text):
        """Редактирование сообщения"""
        try:
            self.vk.messages.edit(
                peer_id=peer_id,
                message_id=message_id,
                message=new_text
            )
            return True
        except Exception as e:
            print(f"Ошибка редактирования сообщения: {e}")
            return False

    def filter_bad_words(self, text):
        """Фильтрация нецензурных слов в тексте"""
        import re

        # Приводим текст к нижнему регистру для поиска
        text_lower = text.lower()

        # Ищем нецензурные слова
        for bad_word in self.bad_words:
            if bad_word in text_lower:
                # Заменяем слово с сохранением регистра
                replacement = self.word_replacements.get(bad_word, '***')

                # Создаем регулярное выражение для поиска с любым регистром
                pattern = re.compile(re.escape(bad_word), re.IGNORECASE)
                text = pattern.sub(replacement, text)

        return text

    def _load_auto_responses(self):
        """Загрузка автоответов из JSON файла"""
        try:
            with open("auto_responses.json", "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"Ошибка загрузки автоответов: {e}")
            return {}


    def get_admins(self, peer_id):
        """Получение администраторов беседы с учетом типа чата"""
        try:
            # Получаем информацию о беседе
            chat_info = self.vk.messages.getConversationsById(peer_ids=peer_id)

            if not chat_info or not chat_info.get('items'):
                return "❌ Не удалось получить информацию о беседе"

            chat = chat_info['items'][0]
            chat_type = chat.get('chat_settings', {}).get('type', 'unknown')

            # Если это групповая беседа
            if chat_type == 'group':
                owner_id = chat['chat_settings']['owner_id']  # ID владельца группы
                return self.get_group_admins(owner_id)

            # Если это личный чат (с участником)
            elif chat_type == 'chat':
                members = self.vk.messages.getConversationMembers(peer_id=peer_id)

                # Проверяем, что список участников не пуст
                if not members.get('items'):
                    return "❌ Нет участников в беседе"

                admins = [member['member_id'] for member in members.get('items', []) if member.get('is_admin')]

                if not admins:
                    return "❌ Администраторы не найдены"

                # Получаем информацию о пользователях
                users_info = self.vk.users.get(user_ids=admins, fields="first_name,last_name")
                admin_list = "\n".join(
                    f"• @id{user['id']} ({user['first_name']} {user['last_name']})" for user in users_info
                )

                return f"👑 Администраторы беседы:\n{admin_list}"

            return "❌ Не удалось определить тип чата"

        except vk_api.exceptions.ApiError as e:
            return f"⚠️ Ошибка API: {e}"
        except Exception as e:
            return f"❌ Ошибка: {e}"


    def get_group_admins(self, owner_id):
        """Получение администраторов для группового чата (где создатель является группой)"""
        try:
            # Получаем информацию о владельце группы
            user_info = self.vk.users.get(user_ids=owner_id, fields="first_name,last_name")
            if user_info:
                user = user_info[0]
                return f"👑 Администратор группы: @id{owner_id} ({user['first_name']} {user['last_name']})"
            return "❌ Не удалось получить информацию о создателе группы"

        except vk_api.exceptions.ApiError as e:
            return f"⚠️ Ошибка API при получении информации о создателе: {e}"
        except Exception as e:
            return f"❌ Ошибка: {e}"


    def _init_moderation_system(self):
        try:
            with open(self.moderators_file, 'r') as f:
                self.moderators = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            self.moderators = [self.owner_id]
        self._save_moderators()

    def _save_moderators(self):
        with open(self.moderators_file, 'w') as f:
            json.dump(self.moderators, f)

    def _is_valid_event(self, event):
        """Проверка валидности события"""
        if not event:
            return False

        # Проверяем базовые атрибуты
        if not hasattr(event, 'type') or event.type is None:
            return False

        # Для событий MESSAGE_NEW проверяем только самые важные атрибуты
        if event.type == VkEventType.MESSAGE_NEW:
            # peer_id и text обязательны
            if not hasattr(event, 'peer_id') or event.peer_id is None:
                return False
            if not hasattr(event, 'text') or event.text is None:
                return False

            # user_id может отсутствовать - это НЕ делает событие невалидным
            # Просто логируем и продолжаем
            if not hasattr(event, 'user_id') or event.user_id is None:
                print(f"⚠️ Событие MESSAGE_NEW без user_id (peer_id={event.peer_id}): '{event.text}'")
                # НЕ возвращаем False - событие все еще валидно!

            return True  # ✅ Всегда возвращаем True для MESSAGE_NEW

        # Для других типов событий
        return True  # ✅ По умолчанию считаем валидными

    def _safe_compare_ids(self, value1, value2):
        """Безопасное сравнение двух ID"""
        try:
            if value1 is None or value2 is None:
                return False
            return int(value1) < int(value2)
        except (TypeError, ValueError):
            return False

    def _safe_handle_event(self, event):
        try:
            if not self._is_valid_event(event):
                return

            # Обрабатываем только MESSAGE_NEW события
            if event.type == VkEventType.MESSAGE_NEW:
                # Передаем на обработку команд
                self.handle_commands(event)

        except Exception:
            pass

    def _get_safe_member_id(self, action):
        try:
            source_mid = action.get('source_mid')
            if source_mid is None:
                return 0
            return int(source_mid)
        except (TypeError, ValueError):
            return 0

    def is_moderator(self, user_id: int) -> bool:
        return user_id in self.moderators

    def _get_replied_user(self, event) -> Optional[int]:
        try:
            # Получаем информацию о сообщении
            msg_info = self.vk.messages.getById(message_ids=event.message_id)

            # Проверяем, что items не пустой
            if not msg_info.get('items') or len(msg_info['items']) == 0:
                print(f"Сообщение с ID {event.message_id} не содержит вложений")
                return None

            # Извлекаем первое сообщение из списка
            replied_msg = msg_info['items'][0].get('reply_message')

            # Проверяем, что reply_message существует и содержит 'from_id'
            if replied_msg and 'from_id' in replied_msg:
                return replied_msg['from_id']
            else:
                print(f"Сообщение с ID {event.message_id} не имеет ответа с 'from_id'")
                return None
        except (vk_api.exceptions.ApiError, KeyError, IndexError) as e:
            print(f"Ошибка получения replied пользователя: {e}")
            return None

    def _resolve_vk_link(self, link: str) -> Optional[int]:
        try:
            clean_link = link.lower().replace('https://', '').replace('http://', '').replace('vk.com/', '').strip()
            if not clean_link:
                return None

            if clean_link.startswith('id'):
                return int(clean_link[2:])

            result = self.vk.utils.resolveScreenName(screen_name=clean_link)
            if result and result.get('type') == 'user':
                return result['object_id']
            return None
        except (vk_api.exceptions.ApiError, ValueError, KeyError) as e:
            print(f"Ошибка разрешения ссылки {link}: {e}")
            return None

    def add_moderator(self, event) -> None:
        try:
            if event.user_id != self.owner_id:
                self.send_message(event.peer_id, "🚫 Только владелец может добавлять модераторов", event.message_id)
                return

            # Пытаемся получить пользователя, на сообщение которого был ответ
            replied_user = self._get_replied_user(event)
            if replied_user and replied_user > 0:
                user_id = replied_user
            else:
                # Если это не ответ, пытаемся извлечь ссылку или упоминание из текста
                parts = event.text.split()
                if len(parts) < 2:
                    raise ValueError("Не указана ссылка или reply")

                link_or_mention = parts[-1]

                # Проверка на упоминание пользователя (формат @username)
                mention_match = re.match(r"@([a-zA-Z0-9_]+)", link_or_mention)
                if mention_match:
                    username = mention_match.group(1)
                    user_id = self._resolve_vk_link(username)
                    if not user_id:
                        raise ValueError("Неверный формат упоминания пользователя")
                else:
                    # Если это ссылка, извлекаем ID пользователя из ссылки
                    user_id = self._resolve_vk_link(link_or_mention)
                    if not user_id:
                        raise ValueError("Неверный формат ссылки")

            # Если пользователь уже модератор
            if user_id in self.moderators:
                user_info = self.vk.users.get(user_ids=user_id, fields='first_name,last_name')[0]
                self.send_message(
                    event.peer_id,
                    f"ℹ️ @id{user_id} ({user_info['first_name']} {user_info['last_name']}) уже модератор",
                    event.message_id
                )
                return

            # Добавляем модератора
            user_info = self.vk.users.get(user_ids=user_id, fields='first_name,last_name')[0]
            self.moderators.append(user_id)
            self._save_moderators()
            self.send_message(
                event.peer_id,
                f"✅ @id{user_id} ({user_info['first_name']} {user_info['last_name']}) добавлен в модераторы",
                event.message_id
            )

        except vk_api.exceptions.ApiError as e:
            print(f"API ошибка при добавлении модератора: {e}")
            self.send_message(event.peer_id, "⚠️ Ошибка VK API при добавлении модератора", event.message_id)
        except ValueError as e:
            print(f"Ошибка обработки: {e}")
            self.send_message(event.peer_id, f"❌ Ошибка: {e}", event.message_id)
        except Exception as e:
            print(f"Ошибка добавления модератора: {e}")
            self.send_message(
                event.peer_id,
                "❌ Используйте:\n1. Ответьте на сообщение командой 'добавить модератора'\n2. Пришлите ссылку вида vk.com/id1 или vk.com/username",
                event.message_id
            )


    def remove_moderator(self, event) -> None:
        try:
            if event.user_id != self.owner_id:
                self.send_message(event.peer_id, "🚫 Только владелец может удалять модераторов", event.message_id)
                return

            replied_user = self._get_replied_user(event)
            if replied_user and replied_user > 0:
                user_id = replied_user
            else:
                parts = event.text.split()
                if len(parts) < 2:
                    raise ValueError("Не указана ссылка или reply")

                link = parts[-1]
                user_id = self._resolve_vk_link(link)
                if not user_id:
                    raise ValueError("Неверный формат ссылки")

            if user_id not in self.moderators:
                user_info = self.vk.users.get(user_ids=user_id, fields='first_name,last_name')[0]
                self.send_message(
                    event.peer_id,
                    f"ℹ️ @id{user_id} ({user_info['first_name']} {user_info['last_name']}) не является модератором",
                    event.message_id
                )
                return

            if user_id == self.owner_id:
                self.send_message(event.peer_id, "🚫 Нельзя удалить владельца", event.message_id)
                return

            user_info = self.vk.users.get(user_ids=user_id, fields='first_name,last_name')[0]
            self.moderators.remove(user_id)
            self._save_moderators()
            self.send_message(
                event.peer_id,
                f"❌ @id{user_id} ({user_info['first_name']} {user_info['last_name']}) удалён из модераторов",
                event.message_id
            )

        except vk_api.exceptions.ApiError as e:
            print(f"API ошибка при удалении модератора: {e}")
            self.send_message(event.peer_id, "⚠️ Ошибка VK API при удалении модератора", event.message_id)
        except Exception as e:
            print(f"Ошибка удаления модератора: {e}")
            self.send_message(
                event.peer_id,
                "❌ Используйте:\n1. Ответьте на сообщение командой 'удалить модератора'\n2. Пришлите ссылку вида vk.com/id1 или vk.com/username",
                event.message_id
            )

    def clear_moderators(self, event) -> None:
        if event.user_id != self.owner_id:
            self.send_message(event.peer_id, "🚫 Только владелец может очистить список", event.message_id)
            return

        self.moderators = [self.owner_id]
        self._save_moderators()
        self.send_message(
            event.peer_id,
            "♻️ Все модераторы удалены (кроме владельца)",
            event.message_id
        )

    def show_moderators(self, event) -> None:
        if not self.is_moderator(event.user_id):
            self.send_message(event.peer_id, "🚫 Только модераторы могут просматривать этот список", event.message_id)
            return

        try:
            if not self.moderators:
                self.send_message(event.peer_id, "📭 Список модераторов пуст", event.message_id)
                return

            mods_info = self.vk.users.get(user_ids=self.moderators, fields="first_name,last_name")
            mod_list = "\n".join(
                f"• @id{mod['id']} ({mod['first_name']} {mod['last_name']})" 
                for mod in mods_info
            )
            self.send_message(
                event.peer_id,
                f"👑 Список модераторов:\n{mod_list}",
                event.message_id
            )
        except vk_api.exceptions.ApiError as e:
            print(f"Ошибка при получении списка модераторов: {e}")
            self.send_message(
                event.peer_id,
                "❌ Ошибка при получении списка модераторов",
                event.message_id
            )

    def _handle_delete_command(self, event):
        try:
            user_id = event.user_id
            peer_id = event.peer_id

            try:
                chat_info = self.vk.messages.getConversationsById(peer_ids=peer_id)
                if not chat_info.get('items'):
                    return
            except vk_api.exceptions.ApiError as api_error:
                if api_error.code in [7, 917]:
                    return
                raise

            if user_id in self.deletion_cooldowns:
                cooldown = 300 - (time.time() - self.deletion_cooldowns[user_id])
                if cooldown > 0:
                    try:
                        self.send_message(
                            peer_id,
                            f"⏳ Лимит: 1 удаление/5 мин. Осталось: {int(cooldown//60)}м {int(cooldown%60)}с",
                            event.message_id
                        )
                    except vk_api.exceptions.ApiError as api_error:
                        if api_error.code not in [7, 917]:
                            print(f"[Ошибка отправки] {api_error}")
                    return

            try:
                msg_info = self.vk.messages.getById(message_ids=event.message_id)
                if not msg_info.get('items'):
                    return

                replied_msg = msg_info['items'][0].get('reply_message')

                if replied_msg and replied_msg['from_id'] == self.bot_id:
                    try:
                        self.vk.messages.delete(
                            message_ids=replied_msg['id'],
                            delete_for_all=1,
                            peer_id=peer_id
                        )
                        status = "✅ Сообщение удалено для всех"
                    except vk_api.exceptions.ApiError as api_error:
                        if api_error.code == 924:
                            self.vk.messages.delete(
                                message_ids=replied_msg['id'],
                                delete_for_all=0
                            )
                            status = "🗑 Сообщение скрыто (только для бота)"
                        elif api_error.code in [7, 917]:
                            return
                        else:
                            raise

                    self.deletion_cooldowns[user_id] = time.time()
                    self.last_deletion_info = {
                        'user': user_id,
                        'msg_id': replied_msg['id'],
                        'time': time.time(),
                        'status': status
                    }

                    # Удаляем только сообщение с подтверждением, не отвечаем
                    self.send_message(peer_id, status, 0)  # Устанавливаем 0 вместо event.message_id

            except vk_api.exceptions.ApiError as api_error:
                if api_error.code not in [7, 917]:
                    print(f"[Ошибка получения сообщения] {api_error}")

        except vk_api.exceptions.ApiError as api_error:
            print(f"[Ошибка VK API] {api_error}")
        except KeyError as key_error:
            print(f"[Ошибка ключа] {key_error}")
        except Exception as error:
            print(f"[Неожиданная ошибка] {error}")
            try:
                self.send_message(
                    event.peer_id,
                    "⚠️ Ошибка при удалении. Попробуйте позже",
                    event.message_id
                )
            except vk_api.exceptions.ApiError as send_error:
                print(f"[Ошибка отправки уведомления] {send_error}")


    def _check_mute_status(self, peer_id):
        current_time = time.time()

        if peer_id is not None and peer_id < 2000000000:  # Проверка на None и проверка ID
            if peer_id in self._last_activity_check:
                if current_time - self._last_activity_check[peer_id] < 300:
                    return peer_id in self._muted_chats

        try:
            self.vk.messages.send(
                peer_id=peer_id,
                message=" ",
                random_id=0,
                disable_mentions=1
            )
            if peer_id in self._muted_chats:
                self._muted_chats.remove(peer_id)
            return False
        except vk_api.exceptions.ApiError as e:
            if e.code in [914, 983]:
                self._muted_chats.add(peer_id)
                return True
            return False
        except Exception:
            return peer_id in self._muted_chats
        finally:
            self._last_activity_check[peer_id] = current_time

    def handle_audio(self, event):
        try:
            msg_info = self.vk.messages.getById(message_ids=event.message_id)
            items = msg_info.get('items', [])

            # Проверка на пустой список
            if not items:
                print(f"Сообщение с ID {event.message_id} не содержит вложений")
                return False

            # Обработка вложений
            for attach in items[0].get('attachments', []):
                if attach['type'] == 'audio':
                    print(f"Найдено аудио-вложение: {attach}")
                    # Логика обработки аудио
                    return True
            return False
        except Exception as e:
            print(f"Ошибка проверки аудио: {e}")
            return False

    def send_message(self, peer_id, text, reply_to=None, attachment=None):
        """Отправка сообщения с уникальным random_id"""
        try:
            # Проверяем, что peer_id корректно задан
            if peer_id is None or peer_id <= 0:
                print(f"Неверный peer_id: {peer_id}")
                return False

            # Проверяем, что текст не пустой и не состоит только из пробелов
            if not text or not str(text).strip():
                print(f"Попытка отправить пустое сообщение: '{text}'")
                return False

            # Создаем параметры для отправки сообщения
            params = {
                'peer_id': peer_id,
                'message': str(text).strip(),
                'random_id': random.randint(1, 10**7),
                'disable_mentions': 1
            }

            # Добавляем ответ на сообщение, если он есть и доступен
            if reply_to is not None and reply_to != 0:
                try:
                    # Проверяем, существует ли сообщение для ответа
                    msg_info = self.vk.messages.getById(message_ids=reply_to)
                    if msg_info.get('items'):
                        params['reply_to'] = int(reply_to)
                    else:
                        print(f"Сообщение {reply_to} не найдено, отправляем без ответа")
                except (TypeError, ValueError, vk_api.exceptions.ApiError) as e:
                    print(f"Ошибка проверки сообщения {reply_to}: {e}. Отправляем без ответа")

            # Добавляем вложения, если они есть
            if attachment:
                params['attachment'] = attachment

            # Отправляем сообщение
            self.vk.messages.send(**params)
            return True

        except vk_api.exceptions.ApiError as api_error:
            # Если ошибка из-за мута
            if api_error.code == 983:
                print(f"❌ Бот не может отправить сообщение в чат {peer_id} — он был замучен.")
                return False
            elif api_error.code == 100:  # Ошибка reply
                print(f"⚠️ Ошибка reply для сообщения {reply_to}. Пытаемся отправить без ответа...")
                # Пытаемся отправить без reply
                try:
                    retry_params = {
                        'peer_id': peer_id,
                        'message': str(text).strip(),
                        'random_id': random.randint(1, 10**7),
                        'disable_mentions': 1
                    }
                    if attachment:
                        retry_params['attachment'] = attachment

                    self.vk.messages.send(**retry_params)
                    return True
                except Exception as retry_error:
                    print(f"Ошибка при повторной отправке: {retry_error}")
                    return False
            elif api_error.code == 10:  # Internal server error
                print("⚠️ Внутренняя ошибка сервера ВК. Пытаемся повторно отправить...")
                # Ждем и пробуем снова
                time.sleep(2)
                try:
                    # Убираем reply_to при повторной отправке
                    retry_params = {
                        'peer_id': peer_id,
                        'message': str(text).strip(),
                        'random_id': random.randint(1, 10**7),
                        'disable_mentions': 1
                    }
                    if attachment:
                        retry_params['attachment'] = attachment

                    self.vk.messages.send(**retry_params)
                    return True
                except Exception as retry_error:
                    print(f"Ошибка при повторной отправке после internal error: {retry_error}")
                    return False
            else:
                print(f"API ошибка при отправке сообщения: {api_error}")
                return False

        except Exception as e:
            print(f"Неизвестная ошибка при отправке сообщения: {e}")
            return False

    def send_message_simple(self, peer_id, text):
        """Упрощенная отправка сообщения"""
        try:
            self.vk.messages.send(
                peer_id=peer_id,
                message=text,
                random_id=random.randint(1, 10**7)
            )
            return True
        except Exception as e:
            print(f"Простая отправка тоже не удалась: {e}")
            return False
            
    def _notify_owner_error(self, error_msg):
        try:
            self.vk.messages.send(
                user_id=self.owner_id,
                message=f"⚠️ Системная ошибка: {error_msg}",
                random_id=0
            )
        except vk_api.exceptions.ApiError:
            pass

    def _unblock_chat(self, peer_id):
        if peer_id in self.blocked_chats:
            self.blocked_chats.remove(peer_id)
            print(f"♻️ Чат {peer_id} разблокирован после таймаута")

    def is_chat_blocked(self, peer_id):
        return peer_id in self.blocked_chats

    def typing_effect(self, peer_id, duration=3):
        if hasattr(self, '_muted_chats') and peer_id in self._muted_chats:
            return

        try:
            start_time = time.time()
            while time.time() - start_time < duration:
                try:
                    self.vk.messages.setActivity(peer_id=peer_id, type="typing")
                except vk_api.exceptions.ApiError as e:
                    if e.code in [914, 983]:
                        if not hasattr(self, '_muted_chats'):
                            self._muted_chats = set()
                        self._muted_chats.add(peer_id)
                        break
                time.sleep(1)
        except Exception:
            pass

    def _safe_api_call(self, method, *args, **kwargs):
        """Безопасный вызов API с обработкой ошибок"""
        try:
            return method(*args, **kwargs)
        except vk_api.exceptions.ApiError as e:
            self._last_api_error = e.code
            if e.code == 5:  # User authorization failed
                logging.warning(f"Ошибка доступа: {e}")
            elif e.code == 917:  # No access to chat
                logging.warning(f"Нет доступа к чату: {e}")
            return None
        except Exception as e:
            logging.error(f"Неизвестная ошибка API: {e}")
            return None

    def get_conversation_members(self, peer_id):
        """Безопасное получение участников беседы"""
        if not peer_id or peer_id < 2000000000:
            return None

        members = self._safe_api_call(
            self.vk.messages.getConversationMembers,
            peer_id=peer_id
        )
        return members.get('items', []) if members else []

    def get_rating_status(self, peer_id):
        return True

    def _is_chat_muted(self, peer_id):
        if peer_id not in self._muted_chats:
            return False

        current_time = time.time()
        if (peer_id in self._last_mute_check and 
            current_time - self._last_mute_check[peer_id] < 300):
            return True

        try:
            self.vk.messages.send(
                peer_id=peer_id,
                message=" ",
                random_id=0,
                disable_mentions=1
            )
            self._muted_chats.remove(peer_id)
            return False
        except vk_api.exceptions.ApiError as e:
            if e.code in [914, 983]:
                self._last_mute_check[peer_id] = current_time
                return True
            return False
        except Exception:
            return True

    def handle_commands(self, event):
        """Обработка команд с автоответами и команд от пользователя"""
        # Безопасное получение user_id
        user_id = getattr(event, 'user_id', None)
        if user_id is None:
            print("Событие без user_id, пропускаем обработку команд")
            return

        if user_id == self.bot_id:  # Игнорируем свои сообщения
            return

        if not hasattr(event, 'text') or event.text is None:
            return

        if not hasattr(event, 'peer_id') or event.peer_id is None:
            return

        try:
            peer_id = int(event.peer_id)
            user_id = int(user_id)
            if peer_id < 2000000000:  # Игнорируем ЛС (личные сообщения)
                return
        except (TypeError, ValueError):
            return

        # Обработка текстовых команд
        text = event.text.strip().lower()

        # Если это команда "кто" или "/кто", проверяем наличие вопроса
        if text.lower().startswith(('кто', '/кто')) or text.lower() in ('кто', '/кто'):
            self.typing_effect(peer_id)
            if text in ('кто', '/кто', 'кто?', '/кто?'):
                self.typing_effect(event.peer_id)
                response = "😆 Я не знаю кого ты хочешь узнать, но я могу тебе подсказать.\n— Напиши кто (вопрос)."
                self.send_message(event.peer_id, response, event.message_id)
                return

            if text.startswith(('кто ', '/кто ')):
                self.typing_effect(event.peer_id)
                # Убираем знаки препинания из текста
                question = text[4:] if text.startswith('/кто ') else text[3:]
                question = re.sub(r'[^\w\s]', '', question)  # Убираем все знаки препинания
                question = question.strip()

                if not question or len(question) < 3:  # Минимум 3 символа для вопроса
                    response = "😆 Ле, надо как минимум указать 3 буквы."
                else:
                    response = self.commands.handle_who(event.peer_id, question)

                self.send_message(event.peer_id, response, event.message_id)
                return

        # ⭐ НОВАЯ КОМАНДА: Повторение сообщений для модераторов
        if text.startswith('/повтори') or text.startswith('/repeat'):
            if self.is_moderator(user_id):
                # Извлекаем текст для повторения (всё после команды)
                original_text = event.text.strip()
                if text.startswith('/повтори'):
                    message_to_repeat = original_text[8:].strip()  # Убираем "/повтори"
                else:  # /repeat
                    message_to_repeat = original_text[7:].strip()  # Убираем "/repeat"

                if message_to_repeat:
                    # ⭐ ФИЛЬТРАЦИЯ НЕЦЕНЗУРНЫХ СЛОВ
                    filtered_message = self.filter_bad_words(message_to_repeat)

                    # Если есть нецензурные слова - показываем предупреждение и редактируем
                    if filtered_message != message_to_repeat:
                        # Сначала отправляем предупреждение БЕЗ ответа
                        warning_msg = "❌ Бот не повторяет матюки, иди помой свои руки."
                        sent_message = self.vk.messages.send(
                            peer_id=peer_id,
                            message=warning_msg,
                            random_id=random.randint(1, 10**7),
                            disable_mentions=1
                        )

                        # Получаем ID отправленного сообщения
                        if sent_message:
                            message_id = sent_message

                            # Ждем 4 секунды и редактируем сообщение
                            def delayed_edit():
                                time.sleep(5)
                                self.edit_message(peer_id, message_id, filtered_message)

                            # Запускаем в отдельном потоке чтобы не блокировать бота
                            import threading
                            thread = threading.Thread(target=delayed_edit)
                            thread.daemon = True
                            thread.start()

                    else:
                        # Если нет мата - просто отправляем сообщение
                        self.send_message(peer_id, filtered_message, reply_to=0)

                    return
                else:
                    self.send_message(peer_id, "❌ Укажите текст для повторения\nПример: /повтори Привет всем!", event.message_id)
                    return
            else:
                self.send_message(peer_id, "🚫 Только модераторы бота могут использовать эту команду", event.message_id)
                return

        # Пробежка по автоответам
        for command, responses in self.auto_responses.items():
            command_variants = command.split(", ")  # Разделяем синонимы по запятой
            if text in command_variants:
                # Проверяем, прошло ли 30 секунд с последнего ответа на эту команду
                current_time = time.time()
                if command in self.last_command_time and current_time - self.last_command_time[command] < 30:
                    return

                self.typing_effect(peer_id, duration=5)
                response = random.choice(responses)
                self.send_message(peer_id, response, event.message_id)
                self.last_command_time[command] = current_time
                return

        # Обработка аудио-вложений
        try:
            if self.commands.get_rating_status(peer_id) and self.commands.is_audio_attachment(event):
                self.commands.rate_music(event, peer_id)
                return
        except Exception as e:
            print(f"Ошибка обработки аудио: {e}")

        # Пробежка по автоответам
        for command, responses in self.auto_responses.items():
            command_variants = command.split(", ")  # Разделяем синонимы по запятой
            if text in command_variants:
                # Проверяем, прошло ли 30 секунд с последнего ответа на эту команду (только для автоответов)
                current_time = time.time()
                if command in self.last_command_time and current_time - self.last_command_time[command] < 30:
                    return  # Игнорируем команду, если она была использована недавно

                # Печатаем сообщение в чате
                self.typing_effect(peer_id, duration=5)

                # Выбираем случайный ответ из списка вариантов
                response = random.choice(responses)

                # Отправляем выбранный ответ
                self.send_message(peer_id, response, event.message_id)

                # Обновляем время последнего ответа на команду
                self.last_command_time[command] = current_time
                return  # Останавливаем обработку после ответа на команду


        # Обработка аудио-вложений
        try:
            if self.commands.get_rating_status(peer_id) and self.commands.is_audio_attachment(event):
                self.commands.rate_music(event, peer_id)
                return
        except Exception as e:
            print(f"Ошибка обработки аудио: {e}")

        # Остальные команды, как в вашем примере:
        if text.lower() in ["+оценки", "-оценки", "оценки"]:
            try:
                chat_info = self.vk.messages.getConversationsById(peer_ids=event.peer_id)
                chat_owner_id = chat_info['items'][0]['chat_settings']['owner_id']
                is_owner = (event.user_id == chat_owner_id)
            except Exception:
                is_owner = False

            is_moderator = self.is_moderator(event.user_id)

            if text == "оценки":
                status = "включены" if self.commands.get_rating_status(peer_id) else "выключены"
                self.send_message(peer_id, f"🔧 Оценки на музыку: {status}\n• +оценки, -оценки (Включить) / (Выключить) - Функция включена везде по дефолту.", event.message_id)
            else:
                enable = (text == "+оценки")
                response = self.commands.set_rating_status(
                    peer_id, 
                    enable, 
                    user_id=event.user_id,
                    is_moderator=(is_owner or is_moderator)
                )
                self.send_message(peer_id, response, event.message_id)
            return


        # Обработка RP-команд  
        text = event.text.strip()

        # Обработка команды /me
        if text.startswith('/я'):
            response = self.commands.handle_me_command(event)
            self.send_message(event.peer_id, response, event.message_id)
            return

        if text.startswith(("+модер", "-модер", "-очистка модеров")):
            if user_id != self.owner_id:
                self.send_message(peer_id, "😆 Не твой уровень, дорогой", event.message_id)
                return

            if text.startswith("+модер"):
                self.add_moderator(event)
            elif text.startswith("-модер"):
                self.remove_moderator(event)
            elif text == "-очистка модеров":
                self.clear_moderators(event)
            return

        if text == "/модеры":
            self.show_moderators(event)
            return

        if text == "удалить":
            if self.is_moderator(user_id):
                self._handle_delete_command(event)
            else:
                self.send_message(peer_id, "🚫 Только модераторы бота могут удалять сообщения", event.message_id)
            return

        if 0 < peer_id < 2000000000:
            self.commands.handle_pm(peer_id)
            return

        fun_command_response = self.fun_commands.handle_command(text)
        if fun_command_response:
            self.send_message(
                peer_id,
                fun_command_response["message"],
                event.message_id,
                fun_command_response.get("attachment")
            )
            return

        if text.lower() == "/mystat":
            self.typing_effect(peer_id)
            response = self.commands.handle_mystat(event.user_id, peer_id)
            self.send_message(peer_id, response, event.message_id)

        elif text.lower() in ["/stat", "/стат", "стат"]:
            self.typing_effect(peer_id)
            try:
                msg = self.vk.messages.getById(message_ids=event.message_id)['items'][0]
                user_id = None

                if 'reply_message' in msg:
                    user_id = msg['reply_message']['from_id']
                elif '@' in text:
                    username = text.split('@')[1].split()[0]
                    user_id = self.vk.users.get(user_ids=username)[0]['id']

                if user_id:
                    response = self.commands.handle_stat(user_id, peer_id, True, self.bot_id)
                else:
                    response = "❌ Укажите пользователя (ответом на сообщение человека)"

                self.send_message(peer_id, response, event.message_id)

            except vk_api.exceptions.ApiError as e:
                print(f"Ошибка в /stat: {e}")
                self.send_message(peer_id, "❌ Ошибка обработки команды", event.message_id)

        elif text.lower() in ["админы", "администрация", "администраторы"]:
            self.typing_effect(peer_id)
            response = self.commands.handle_admins(peer_id, text)
            if response:
                self.send_message(peer_id, response, event.message_id)

        elif any(w in text.lower() for w in ["погода в аду", "!погода"]):
            self.typing_effect(peer_id)
            response = self.commands.handle_weather()
            self.send_message(peer_id, response, event.message_id)

        elif text.lower() in ["погода в раю", "!рай"]:
            self.typing_effect(peer_id)
            response = self.commands.handle_paradise_weather()
            self.send_message(peer_id, response, event.message_id)

        elif text.lower() in ["/help", "/помощь", "команды"]:
            self.typing_effect(peer_id)
            response = self.commands.handle_help()
            self.send_message(peer_id, response, event.message_id)

    def run(self):
        print("Bot started!")
        while True:
            try:
                for event in self.longpoll.listen():
                    try:
                        if event.type == VkEventType.MESSAGE_NEW:
                            # Проверка на валидность события
                            if not self._is_valid_event(event):
                                print(f"Невалидное событие: {event}")  # ✅ Есть переменная
                                continue

                            # Получаем peer_id и проверяем его
                            peer_id = event.peer_id
                            if peer_id is None or peer_id < 2000000000:  # Игнорируем ЛС
                                continue

                            # Обработка события
                            self._safe_handle_event(event)

                    except Exception as ex:
                        print(f"Ошибка обработки события: {ex}")  # ✅ Есть переменная
                        continue

            except vk_api.exceptions.ApiError as api_error:
                print(f"Ошибка API: {api_error}")  # ✅ Есть переменная
                time.sleep(5)
            except Exception as e:
                print(f"Неизвестная ошибка: {e}")  # ✅ Добавил переменную
                time.sleep(10)
                
if __name__ == "__main__":
    bot = VKBot()
    bot.run()