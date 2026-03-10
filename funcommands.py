class FunCommands:
    def __init__(self, vk_api):
      self.vk = vk_api
    
      # 1. Видео-команды (очко, очкошник, трус)
      self.video_commands = {
          "очко": "Маслиат пацанчики! 🤣",
          "очкошник": "Тише пацаны, а то я начну щас. 🤣",
          "очконул": "Ты тоже бра не лучше 🤣",
      }
      self.video_attachment = "video388905015_456239090"
    
      # 2. Видео-команды (иди нах/пнх)
      self.video_commands_2 = {
          "иди нахуй": "Туда, этого безбожника!",
          "пнх": "Сам иди лье",
          "пошёл нахуй": "Ах ты ж..." 
      }
      self.video_attachment_2 = "video708740556_456239943"
    
      # 3. Фото-команды
      self.photo_commands = {
          "стикеры": "Мне тоже подари да вацчлен",
          "подари стикеры": "Тоже хочу!",
          "стикеры подари": "Не отказался бы тоже.",
          "мои стикеры": "Твои стикеры не интересует, лучше подари их!",
      }
      self.photo_attachment = "photo22204798_457240714"
    
      self.photo_commands_2 = {
          "@sufist_bot": "💢 Ты не достоин меня даже звать!",
      }
      self.photo_attachment_2 = "photo22204798_457240491"
    
      # 4. Гиф-команды
      self.gif_commands = {
          "чурка": "Он уже преврашается в чурку, после твоих высказываний"
      }
      self.gif_attachment = "doc22204798_667296122"
    
    # 5. НОВАЯ КОМАНДА - Снятие мутов ⭐
      self.unmute_commands = {
        "кай очистить муты": "Ок.",
        "сними мут": "Ок.", 
        "очисти муты": "Ок.",
        "размуть": "Ок.",
        "убери мут": "Ок.",
        "снять мут": "Ок.",
        "-мут": "Ок.",
        "очистить муты": "Ок."
      }
      self.unmute_attachment = "photo22204798_457240716"

    def handle_command(self, text):
        """Обработка текстовых команд"""
        text = text.lower().strip()
    
        # Проверка упоминаний бота
        for trigger in self.photo_commands_2:
            if trigger.lower() in text:
                return {
                    "message": self.photo_commands_2[trigger],
                    "attachment": self.photo_attachment_2
                }
    
        # 1. Проверка видео-команд (группа 1)
        if text in self.video_commands:
            return {
                "message": self.video_commands[text],
                "attachment": self.video_attachment
            }
    
        # 2. Проверка видео-команд (группа 2)
        elif text in self.video_commands_2:
            return {
                "message": self.video_commands_2[text],
                "attachment": self.video_attachment_2
            }
    
        # 3. Проверка фото-команд
        elif text in self.photo_commands:
            return {
                "message": self.photo_commands[text],
                "attachment": self.photo_attachment
            }
    
        # 4. Проверка НОВОЙ команды снятия мутов
        elif text in self.unmute_commands:
            return {
                "message": self.unmute_commands[text],
                "attachment": self.unmute_attachment
            }
    
        # 5. Проверка гиф-команд
        elif text in self.gif_commands:
            return {
                "message": self.gif_commands[text],
                "attachment": self.gif_attachment
            }
    
        return None

def handle_commands(self, event):
  """Обработка команд с автоответами и команд от пользователя"""
  if event.user_id == self.bot_id:  # Игнорируем свои сообщения
      return

  if not hasattr(event, 'text') or event.text is None:
      return

  if not hasattr(event, 'peer_id') or event.peer_id is None:
      return

  try:
      peer_id = int(event.peer_id)
      user_id = int(event.user_id)
      if peer_id < 2000000000:  # Игнорируем ЛС (личные сообщения)
          return
  except (TypeError, ValueError):
      return

  # Проверка на добавление бота в беседу
  if hasattr(event, 'raw') and isinstance(event.raw, list):
      if len(event.raw) > 6 and event.raw[6] == 'chat_invite_user' and event.raw[3] == self.bot_id:
          self._handle_bot_added(event)

  # Проверка блокировки и мута чата
  if peer_id in self.blocked_chats or self._is_chat_muted(peer_id):
      return

  # Обработка текстовых команд
  text = event.text.strip().lower()

  # Проверка текста команды
  text = event.text.strip().lower()
  user_id = event.user_id
  peer_id = event.peer_id

  if text == "сбросить намазы":
      # Проверка, является ли пользователь модератором
      if not self.is_moderator(user_id):
          self.send_message(peer_id, "❌ Вы не являетесь модератором этого чата.", event.message_id)
          return

      # Сбросим все намазы для чата
      self.namaz_commands.reset_namazs_in_chat(peer_id)  # Сбросим данные

      # Подтверждаем успешное выполнение команды
      self.send_message(peer_id, "✅ Все намазы были сброшены в этой беседе. Статистика начинается с нуля.", event.message_id)
      return

  # Команды для намазов
  if text == "намаз":
      response = self.namaz_commands.handle_namaz(event)  # Используем NamazCommands
      self.send_message(event.peer_id, response, event.message_id)
      return

  elif text == "мои намазы":
      response = self.namaz_commands.handle_my_namaz(event)  # Используем NamazCommands
      self.send_message(event.peer_id, response, event.message_id)
      return

  elif text == "топ намазов":
      response = self.namaz_commands.handle_top_namaz(event)  # Используем NamazCommands
      self.send_message(event.peer_id, response, event.message_id)
      return