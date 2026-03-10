import random
import json
import os
import time
from vk_api.exceptions import ApiError
import logging
import vk_api
from datetime import datetime

class Commands:
    def __init__(self, vk_api):
        self.vk = vk_api
        self.user_cache = {}
        self.blocked_chats = set()
        self.music_rating_enabled = True
        self._last_api_error = None
        self._ratings_file = 'ratings_status.json'  # Приватная переменная

        self.rating_messages = [
            "🍷 Этот трек – как алкоголь в Рамадан: харам, но {}/10!",
            "🎲 Этот бит – как азарт в пятницу: грешно, но {}/10!", 
            "🤲 Одной рукой ставлю {}/10, другой — читаю истигфар",
            "🚗 В такси включать опасно — водитель начнёт гонять. {}/10"
            "📿 Я спросил у муллы – он сказал 'харам'. Но я всё равно ставлю {}/10!",
            "💥 Такого харама я не слышал со времён последнего джихана! {}/10!",
            "🎲 Этот трек – как суфий на маджлисе: вроде в теме, но нет. {}/10!",
            "😂 После такого трека даже имам пустил слезу... но от смеха! {}/10!",
            "🛌 Слушать перед сном - гарантированные греховные сны. {}/10",
            "👎 Не буду даже оценивать такую шнягу, скидывай норм треки.",
            "🛐 Слушал в наушниках — иншаАллах, никто не видел. {}/10",
            "🍚 Этот трек - как плов без морковки: не по-нашему, но вкусно. {}/10",
            "🤲 Ставлю {}/10 и делаю дуа, чтобы никто не узнал, что мне понравилось!"

        ]
        self._ratings_status = self._load_ratings_status()

        # Все текстовые ответы
        self.WEATHER_JOKES = [
            "🔥 777°C - стандартная температура для грешников, слушающих музыку",
            "🌪 Ветер с Кавказа несёт запах жареной шаурмы и несбывшихся надежд",
            "💀 Видимость как у таксиста, который 'не берёт женщин",
            "🌡 Давление как у муллы, увидевшего девушку без платка",
            "☁️ Облачность 100% - как вероятность попадания сюда всех из этой беседы",
            "⚡ Молнии бьют исключительно по качалкам и кальянным",
            "👹 Местные жители сегодня злее, чем чеченец в московской пробке",
            "💧 Влажность 99% - это слёзы матерей, чьи сыновья стали тиктокерами",
            "🧯 Пожарная опасность - критическая, особенно в районе греховных мыслей",
            "🚬 Воздух на 70% состоит из запрещённых веществ и сплетен",
            "🕌 Ветер перемен дует с востока, но все равно приносит харам",
            "🍢 На улицах шашлык из тех, кто не верил в ад",
            "☄️ Температура как в телеграм-чате кавказских родственников после новости о свадьбе без их согласия",
            "💣 Ветер несёт обломки разрушенных качалок и фразы 'ты меня уважаешь?'",
            "🧨 Давление как у Руслана из Тюмени, когда его называют 'дагестанцем'",
            "🌋 Лава состоит из сплетен махачкалинских тётушек и пролитого айрана",
            "⚰️ Видимость как у парня на мерседесе с затемнёнными стёклами - ноль, но он всё равно едет"
        ]

        self.PARADISE_WEATHER = [
            "🌞 Температура: +25°C (кондиционеры от Аллаха включены)",
            "🕊 Ветер: лёгкий, несёт запах плова и одобрения родственников",
            "🌿 Воздух: свежесть, как после дуа на рассвете (но без будильника)",
            "🍇 Осадки: капли айрана и град халвы",
            "🕌 Видимость: идеальная — даже имам без очков видит грешников",
            "🍯 Влажность: 69% (но это халал, потому что в раю)",
            "🦚 Птицы поют: 'Ля иляхэ илля Ллах', но в бите",
            "🌅 Закат: вечный, как обещания 'завтра начну поститься'",
            "🍖 Гриль: ангелы жарят шашлык без очереди",
            "☕ Утро: кофе уже готов — его принёс джинн-бариста",
            "🛐 Молитва: все вовремя, но можно и позже (в раю же!)",
            "🚗 Пробок нет — все на верблюдах-феррари",
            "📿 WiFi: 100500 Мбит/с, без блокировок",
            "💃 Танцы: разрешены, но только лезгинку (и то шепотом)"
        ]

        self.WHO_RESPONSES = [
            "Как главный Мулла РД, заявляю что - {}",
            "Не знаю что тебе джинарики сказали, но я думаю что - {}",
            "Воробьи суфистские несут мне что - {}",
            "Клянусь своей тюбетейкой, что - {}",
            "В газете 'Ас-салам' написано, что - {}",
            "Только что Сергей Меликов написал мне, и подтвердил что - {}",
            "😆 Хватит да уже, тут вывод только один, и это ты -",
            "Ставлю свое нехарамное очко что - {}",
            "Мои лезгинские предки подсказали что - {}"
        ]

    def handle_me_command(self, event) -> str:
        """
        Обработка команды /me
        Формат: /me <действие от 5 букв>
        """
        try:
            # Разбиваем текст на части
            parts = event.text.strip().split()

            # Проверяем есть ли действие после /me
            if len(parts) < 2:
                return "🐒 Лабан, введи свое действие."

            # Извлекаем действие (всё после /me)
            action = ' '.join(parts[1:])

            # Проверка длины действия
            if len(action) < 5:
                return "😆 Буквы когда платными стали? (5 букв минимум)"

            # Получаем информацию об отправителе
            user_info = self.vk.users.get(
                user_ids=event.user_id,
                fields='first_name,last_name'
            )[0]

            # Формируем сообщение
            message = f"— @id{event.user_id} ({user_info['first_name']} {user_info['last_name']}) сейчас: {action}"

            # Отправляем сообщение в чат или беседу
            self.vk.messages.send(
                peer_id=event.peer_id,  # peer_id указывает на чат или беседу, куда отправляется сообщение
                message=message,
                random_id=0  # random_id нужен для предотвращения повторной отправки
            )

            # Возвращаем пустое сообщение, так как ответ уже был отправлен
            return ""

        except Exception as e:
            logging.error(f"Ошибка в handle_me_command: {e}")
            return "Ошибка обработки команды"

    def _load_ratings_status(self):
        """Загрузка статуса оценок из файла"""
        if os.path.exists(self._ratings_file):
            with open(self._ratings_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}

    def _save_ratings_status(self):
        """Сохранение статуса оценок в файл"""
        with open(self._ratings_file, 'w', encoding='utf-8') as f:
            json.dump(self._ratings_status, f, ensure_ascii=False, indent=2)

    def get_rating_status(self, peer_id):
        """Проверка статуса оценок для беседы"""
        return self._ratings_status.get(str(peer_id), True)  # По умолчанию True

    def set_rating_status(self, peer_id, enable, user_id=None, is_moderator=False):
        """Устанавливает статус оценок (создатель беседы или модератор бота)"""
        # Проверка кулдауна (1 минута)
        last_change = self._ratings_status.get(f"{peer_id}_last_toggle", 0)
        current_time = time.time()

        if current_time - last_change < 60:
            remaining = int(60 - (current_time - last_change))
            return f"⏳ Лимит: 1 раз в минуту! Жди {remaining} сек."

        if not is_moderator:
            return "🚫 Только создатель беседы может менять статус оценок."

        # Обновляем статус
        self._ratings_status[str(peer_id)] = enable
        self._ratings_status[f"{peer_id}_last_toggle"] = current_time
        self._save_ratings_status()

        status = "включены ✅" if enable else "выключены ❌"
        return f"⚡ Оценки музыки {status} (настроил @id{user_id})"

    def rate_music(self, event, peer_id):
        if not self.get_rating_status(peer_id):
            return False

        try:
            # Добавьте эту проверку
            if not self.is_audio_attachment(event):
                return False

            # Остальная логика...
        except Exception as e:
            print(f"Ошибка оценки музыки: {e}")
            return False

        """Оценка музыкального трека с правильной структурой"""
        if not self.get_rating_status(peer_id):
            return False

        try:
            # Проверка на аудио вложение
            if not self.is_audio_attachment(event):
                return False

            # Получение данных сообщения
            msg_data = self.vk.messages.getById(message_ids=event.message_id)
            items = msg_data.get('items', [])
            if not items:
                return False

            # Поиск аудио вложения
            for attach in items[0].get('attachments', []):
                if attach.get('type') != 'audio':
                    continue  # Пропускаем неаудио вложения

                try:
                    # Отправка оценки
                    rating = random.randint(0, 10)
                    self.vk.messages.send(
                        peer_id=peer_id,
                        message=random.choice(self.rating_messages).format(rating),
                        reply_to=event.message_id,
                        random_id=random.randint(1, 10**7),
                        disable_mentions=1
                    )
                    return True  # Успешная оценка

                except ApiError as api_error:
                    if api_error.code in [914, 983]:  # Обработка ограничений
                        self.blocked_chats.add(peer_id)
                    return False

            return False  # Если не найдено подходящее аудио

        except Exception:
            return False


    def is_audio_attachment(self, event):
        """Проверка на аудио вложение с защитой от ошибок доступа"""
        if not hasattr(event, 'message_id'):
            return False

        msg_data = self._safe_api_call(
            self.vk.messages.getById, message_ids=event.message_id
        )

        # Проверка, что в items есть элементы
        if not msg_data or not msg_data.get('items'):
            return False

        # Проверка на аудио вложение
        for attach in msg_data['items'][0].get('attachments', []):
            if attach.get('type') in ['audio', 'audio_message']:
                return True

        return False


    def handle_paradise_weather(self):
        """Обработка команды 'погода в раю'"""
        return f"🌴 Погода в Раю:\n{random.choice(self.PARADISE_WEATHER)}"

    def handle_pm(self, peer_id):
        """Обработка личных сообщений"""
        self.vk.messages.send(
            user_id=peer_id,
            message="❌ Бот работает только в беседах, пригласи меня в беседу!",
            random_id=random.randint(1, 10**7)
        )

    # Обработка команды /mystat
    def handle_mystat(self, user_id, peer_id):
        """Обработка команды /mystat с новой информацией"""
        user_info = self._get_user_info(user_id, peer_id)

        if user_info:
            return (
                f"📌 Информация:\n\n"
                f"— {user_info['gender']}: [id{user_info['id']}|{user_info['name']}]\n"  # Здесь пол
                f"💳 Возраст: {user_info['bdate']}\n"
                f"👥 Аудитория: {user_info['friends']} Др, {user_info['followers']} Пдп.\n"
                f"🏙️ Город: {user_info['city']}\n"
                f"⛓️ ID: {user_info['id']}\n"
                f"🔐 Тип аккаунта: {user_info['account_type']}\n"
                f"🤵 Должность: {user_info['role']}\n"
                f"✉️ Статус:\n{user_info['status']}"
            )
        return "❌ Не удалось получить информацию"

    # Обработка команды /stat
    def handle_stat(self, user_id, peer_id, is_reply=False, bot_id=None):
        """Обработка команды /stat с расширенной информацией"""
        if not is_reply:
            return "❌ Ответь на сообщение человека командой /stat"

        if user_id == bot_id:
            return "🚫 Ошибка: На меня эта хуйня не работает"

        user_info = self._get_user_info(user_id, peer_id)
        if user_info:
            return (
                f"📌 Информация:\n\n"
                f"— {user_info['gender']}: [id{user_info['id']}|{user_info['name']}]\n"
                f"💳 Др: {user_info.get('bdate', 'Не указана')}\n"
                f"👥 Аудитория: {user_info.get('friends', '?')} Др, {user_info.get('followers', '?')} Пдп.\n"
                f"🏙️ Город: {user_info['city']}\n"
                f"⛓️ ID: {user_info['id']}\n"
                f"🔐 Тип аккаунта: {user_info['account_type']}\n"
                f"🤵 Должность: {user_info['role']}\n"
                f"💡 Активность: {random.choice(['сегодня', 'вчера', 'неделю назад', 'онлайн'])}\n"
                f"✉️ Статус:\n{user_info['status']}"
            )
        return "❌ Не удалось получить информацию"

    def handle_who(self, peer_id, question):
        """Обработка команды кто с улучшенной проверкой"""
        member = self._get_random_member(peer_id)
        if not member:
            return "❌ Не удалось выбрать участника"

        response_template = random.choice(self.WHO_RESPONSES)
        return f"{response_template.format(member)} {question}"

    def handle_admins(self, peer_id, message_text):
        """Обработка команды админы"""
        try:
            # Получаем список участников беседы
            members_data = self.vk.messages.getConversationMembers(peer_id=peer_id)

            # Проверка на наличие данных
            if 'items' not in members_data or not members_data['items']:
                return "❌ В беседе нет участников или не удалось получить информацию."

            members = members_data['items']
            admins = []
            owner = None

            # Проходим по участникам и ищем владельца и администраторов
            for member in members:
                if 'is_owner' in member and member['is_owner']:
                    owner = member['member_id']
                elif member.get('is_admin', False):
                    admins.append(member['member_id'])

            response = "👑 Администрация беседы:\n"

            # Если найден владелец (создатель беседы)
            if owner:
                user_info = self.vk.users.get(user_ids=owner, fields="first_name,last_name")
                if user_info:
                    user = user_info[0]
                    response += f"• Создатель: [id{owner}|{user['first_name']} {user['last_name']}]\n"
                else:
                    response += "❌ Не удалось получить информацию о создателе.\n"

            # Если найдены администраторы
            if admins:
                admin_users = self.vk.users.get(user_ids=admins, fields="first_name,last_name")
                for user in admin_users:
                    response += f"• Подстилка Админа: [id{user['id']}|{user['first_name']} {user['last_name']}]\n"
            else:
                response += "❌ Администраторы не найдены.\n"

            return response

        except vk_api.exceptions.ApiError as e:
            print(f"API ошибка при получении админов: {e}")
            return "❌ Ошибка API при получении списка администраторов"
        except Exception as e:
            print(f"Ошибка получения списка админов: {e}")
            return "❌ Не удалось получить список администраторов"


    def handle_weather(self):
        """Обработка команды погода"""
        return f"🌡 Погода в аду:\n{random.choice(self.WEATHER_JOKES)}"

    def handle_help(self):
        """Обработка команды /help"""
        return (
            "📚 Справочная бота:\n"
            "[vk.com/@sufist_bot-commands|✔️ Просьба почитать доступные команды!]\n"
        )

    def _get_user_info(self, user_id, peer_id=None):
        if not user_id or user_id < 0:  # Проверка на валидность ID
            return None

        try:
            if user_id in self.user_cache:
                cached_info = self.user_cache[user_id]
                if peer_id and peer_id > 2000000000:
                    # Обновляем только роль для кешированных данных
                    cached_info['role'] = self._get_user_role(user_id, peer_id)
                return cached_info

            # Запрос данных с защитой от пустого ответа
            users_data = self.vk.users.get(
                user_ids=user_id,
                fields='city,status,sex,is_closed,bdate,counters'
            )

            if not users_data or len(users_data) == 0:
                print(f"Пользователь {user_id} не найден")
                return None

            user = users_data[0]

            # Основная информация
            gender = "Грешник" if user.get('sex') == 2 else "Грешница" if user.get('sex') == 1 else "Чмо"
            account_type = "Закрытый очкошник" if user.get('is_closed', True) else "Открытый"

            # Дата рождения с защитой от ошибок
            bdate_info = "Не указана"
            if 'bdate' in user:
                try:
                    bdate_parts = user['bdate'].split('.')
                    if len(bdate_parts) >= 3:
                        age = datetime.now().year - int(bdate_parts[2])
                        bdate_info = f"{user['bdate']} ({age} лет)"
                    else:
                        bdate_info = user['bdate']
                except (ValueError, TypeError, IndexError):
                    bdate_info = user.get('bdate', 'Не указана')

            # Социальные счетчики
            counters = user.get('counters', {})
            friends = counters.get('friends', '?')
            followers = counters.get('followers', '?')

            # Намазы
            namaz_count = random.randint(0, 5)
            namaz_status = "кяфир 💀" if namaz_count == 0 else "🦁" if namaz_count >= 3 else "✔️"

            # Получаем роль (отдельный метод для удобства)
            role = self._get_user_role(user_id, peer_id) if peer_id and peer_id > 2000000000 else "РАБ АКТИВА"

            user_info = {
                'name': f"{user.get('first_name', '')} {user.get('last_name', '')}",
                'city': user.get('city', {}).get('title', 'Не указан'),
                'id': user.get('id', 0),
                'status': user.get('status', 'Без статуса'),
                'gender': gender,
                'account_type': account_type,
                'role': role,
                'bdate': bdate_info,
                'friends': friends,
                'followers': followers,
                'namaz': f"{namaz_count} {namaz_status}"
            }

            self.user_cache[user_id] = user_info
            return user_info

        except ApiError as e:
            print(f"Ошибка VK API: {e}")
            return None
        except Exception as e:
            print(f"Неожиданная ошибка: {e}")
            return None

    def _get_user_role(self, user_id, peer_id):

        if user_id is None:
            return None
        try:
            user_id = int(user_id)
            if user_id <= 0:
                return None
        except (TypeError, ValueError):
            return None

        """Определение роли пользователя в беседе"""
        try:
            # Сначала проверяем создателя беседы
            chat_info = self.vk.messages.getConversationsById(peer_ids=peer_id)
            if chat_info.get('items'):
                owner_id = chat_info['items'][0]['chat_settings']['owner_id']
                if user_id == owner_id:
                    return "СОЗДАТЕЛЬ БС 🌟"

            # Затем проверяем администраторов
            members = self.vk.messages.getConversationMembers(peer_id=peer_id)
            for member in members.get('items', []):
                if member.get('member_id') == user_id:
                    if member.get('is_admin'):
                        return "ПОЩЕЧИНА АДМИНА ⭐"
                    break

            return "РАБ АКТИВА"
        except Exception as e:
            print(f"Ошибка проверки роли: {e}")
            return "РАБ АКТИВА"

    def _safe_api_call(self, method, *args, **kwargs):
        """Безопасный вызов API с обработкой ошибок"""
        try:
            return method(*args, **kwargs)
        except Exception as e:
            self._last_api_error = str(e)
            logging.error(f"API ошибка: {e}")
            return None

    def _get_random_member(self, peer_id):
        """Безопасное получение случайного участника беседы"""
        try:
            if not peer_id or peer_id < 2000000000:
                return None

            # Используем self._safe_api_call вместо self.vk напрямую
            members_data = self._safe_api_call(
                self.vk.messages.getConversationMembers,
                peer_id=peer_id
            )

            if not members_data or 'items' not in members_data:
                return None

            valid_members = []
            for member in members_data['items']:
                try:
                    if isinstance(member, dict) and 'member_id' in member:
                        member_id = member['member_id']
                        if isinstance(member_id, int) and member_id > 0:
                            valid_members.append(member_id)
                except Exception:
                    continue

            if not valid_members:
                return None

            user_id = random.choice(valid_members)
            user_data = self._safe_api_call(
                self.vk.users.get,
                user_ids=user_id
            )

            if not user_data or not isinstance(user_data, list):
                return None

            user = user_data[0]
            return f"[id{user_id}|{user['first_name']} {user['last_name']}]"

        except Exception as e:
            logging.error(f"Ошибка в _get_random_member: {e}")
            return None