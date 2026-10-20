# 3x-ui (MHSanaei) Monitor for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/default)
[![GitHub Release](https://img.shields.io/badge/release-v1.0.0-blue.svg)](https://github.com/MHSanaei/3x-ui)

HACS-совместимая интеграция для Home Assistant для **read-only мониторинга** панели [3x-ui (форк MHSanaei)](https://github.com/MHSanaei/3x-ui).

Интеграция собирает системные метрики сервера, контролирует статус ядра Xray-core, отслеживает суммарный трафик, а также **автоматически создает индивидуальные сенсоры для каждого вашего Inbound-порта** (статус работы, число клиентов, трафик).

---

## ✨ Возможности

- 🚀 **Настройка через UI (Config Flow)**: ввод URL и Bearer-токена в интерфейсе Home Assistant.
- 🌐 **Мультисерверность**: возможность добавить сколько угодно панелей 3x-ui (например, "VPS Франкфурт", "VPS Амстердам"). Каждая панель формирует собственное устройство (Device) в Home Assistant.
- 🔒 **Поддержка HTTP и HTTPS**: работает как по обычному незащищенному `http://`, так и по `https://` с поддержкой отключения проверки самоподписанных SSL-сертификатов.
- 🔄 **Автообнаружение инбаундов**: при добавлении нового порта в 3x-ui сенсоры создаются автоматически без перезагрузки Home Assistant.
- 📊 **Нативные счетчики трафика**: сенсоры имеют `state_class: total_increasing` и единицу `B` (байты), что позволяет Home Assistant автоматически отображать значения в КБ/МБ/ГБ/ТБ и использовать помощник **Utility Meter** для учета трафика за день/месяц.
- 🧭 **Мониторинг аутбаундов**: сенсор с подсчетом и списком настроенных Outbounds (direct, warp, wireguard и т.д.) в атрибутах.

---

## 📦 Установка

### Вариант 1: Вручную (быстро и просто)
1. Скопируйте папку `custom_components/three_x_ui` в папку `config/custom_components/` вашего Home Assistant.
2. Перезагрузите Home Assistant (**Настройки ➔ Система ➔ Перезагрузить**).

### Вариант 2: Через HACS (Custom Repository)
1. Откройте **HACS** в Home Assistant.
2. В верхнем правом углу нажмите три точки ➔ **Пользовательские репозитории** (Custom repositories).
3. Укажите ссылку на этот репозиторий, тип — **Интеграция** (Integration).
4. Нажмите **Добавить**, найдите интеграцию **3x-ui Monitor** и нажмите **Загрузить**.
5. Перезагрузите Home Assistant.

---

## 🔑 Где взять API Token в 3x-ui?

1. Войдите в веб-интерфейс вашей панели 3x-ui (MHSanaei).
2. Перейдите в меню **Настройки панели** (Panel Settings) ➔ **Безопасность** (Security) или вкладку **API Token**.
3. Сгенерируйте и скопируйте **API Token**.
4. Сохраните настройки панели и перезапустите панель, если потребуется.

---

## ⚙️ Настройка в Home Assistant

1. Перейдите в **Настройки ➔ Устройства и службы ➔ Добавить интеграцию**.
2. В поиске введите **3x-ui Monitor**.
3. Заполните форму:
   - **Название сервера**: например, `VPS Frankfurt`
   - **URL панели**: полный URL с портом и путем, например `http://192.168.1.100:2053` или `https://my-vps.com:2053/secret_path`
   - **API Token (Bearer)**: скопированный токен из настроек панели
   - **Проверять SSL-сертификат**: снимите галочку, если используете самоподписанный HTTPS или обычный HTTP
   - **Интервал обновления**: по умолчанию 30 секунд

---

## 📊 Создаваемые сущности

### Системные сенсоры (для каждого сервера):
| Сущность | Назначение |
| :--- | :--- |
| `binary_sensor.<сервер>_xray_core_status` | Статус работы Xray-core (Running/Stopped) |
| `sensor.<сервер>_cpu_usage` | Нагрузка на процессор (%) |
| `sensor.<сервер>_memory_usage` | Использование оперативной памяти (%) |
| `sensor.<сервер>_memory_used` / `_total` | Объем памяти (байты, с авто-конвертацией в MB/GB) |
| `sensor.<сервер>_disk_usage` | Использование диска (%) |
| `sensor.<сервер>_disk_used` / `_total` | Объем диска (байты, с авто-конвертацией в GB) |
| `sensor.<сервер>_server_uptime` | Время непрерывной работы сервера |
| `sensor.<сервер>_tcp_connections` | Количество активных TCP соединений |
| `sensor.<сервер>_udp_connections` | Количество активных UDP соединений |
| `sensor.<сервер>_total_upload` | Суммарный Upload трафик по всем портам |
| `sensor.<сервер>_total_download` | Суммарный Download трафик по всем портам |
| `sensor.<сервер>_total_clients` | Общее количество клиентов на сервере |
| `sensor.<сервер>_active_inbounds` | Количество включенных инбаундов |
| `sensor.<сервер>_outbounds_configured` | Список аутбаундов (в атрибутах) |

### Сенсоры инбаундов (создаются для каждого порта):
| Сущность | Назначение |
| :--- | :--- |
| `binary_sensor.<сервер>_inbound_<remark>_status` | Активен ли конкретный инбаунд (On/Off) |
| `sensor.<сервер>_inbound_<remark>_clients` | Число клиентов на инбаунде (список в атрибутах) |
| `sensor.<сервер>_inbound_<remark>_upload` | Трафик отдачи данного инбаунда |
| `sensor.<сервер>_inbound_<remark>_download` | Трафик загрузки данного инбаунда |

---

## 📈 Учет трафика за день и месяц (Utility Meter)

Поскольку сенсоры отдают монотонно растущие счетчики (`state_class: total_increasing`), настроить учет трафика за день/месяц можно за 1 минуту:

1. В Home Assistant откройте **Настройки ➔ Устройства и службы ➔ Помощники** (Helpers).
2. Нажмите **+ Создать помощника** ➔ **Счетчик коммунальных услуг** (Utility Meter).
3. Выберите входной сенсор: `sensor.<ваш_сервер>_total_download`.
4. Задайте период сброса: **Ежедневно** (или **Ежемесячно**).
5. Нажмите **Создать**. Теперь у вас есть точный сенсор трафика за текущие сутки!

---

## 🎨 Примеры карточек для Lovelace Дашборда

### Вариант 1: Mushroom Cards (Современный стиль)
Требуется HACS-плагин `lovelace-mushroom` (если установлен):

```yaml
type: vertical-stack
cards:
  # Заголовок сервера и статус
  - type: custom:mushroom-template-card
    primary: "VPS Франкфурт (3x-ui)"
    secondary: >
      Xray: {{ 'Работает' if is_state('binary_sensor.3x_ui_server_xray_core_status', 'on') else 'Остановлен' }} |
      Клиентов: {{ states('sensor.3x_ui_server_total_clients') }}
    icon: mdi:server-network
    icon_color: "{{ 'green' if is_state('binary_sensor.3x_ui_server_xray_core_status', 'on') else 'red' }}"

  # Чипы с быстрыми метриками
  - type: custom:mushroom-chips-card
    chips:
      - type: entity
        entity: sensor.3x_ui_server_cpu_usage
        icon_color: blue
      - type: entity
        entity: sensor.3x_ui_server_memory_usage
        icon_color: orange
      - type: entity
        entity: sensor.3x_ui_server_disk_usage
        icon_color: purple
      - type: entity
        entity: sensor.3x_ui_server_active_inbounds
        icon_color: green

  # Суммарный трафик
  - type: horizontal-stack
    cards:
      - type: custom:mushroom-entity-card
        entity: sensor.3x_ui_server_total_download
        name: "Всего Скачано"
        icon: mdi:download-network
        icon_color: cyan
      - type: custom:mushroom-entity-card
        entity: sensor.3x_ui_server_total_upload
        name: "Всего Отдано"
        icon: mdi:upload-network
        icon_color: deep-orange

  # Список инбаундов
  - type: entities
    title: "Инбаунды (Inbounds)"
    entities:
      - entity: binary_sensor.3x_ui_server_inbound_1_status
        name: "VLESS Reality (Порт 443)"
      - entity: sensor.3x_ui_server_inbound_1_clients
        name: "Клиентов на VLESS"
      - entity: sensor.3x_ui_server_inbound_1_download
        name: "Трафик VLESS"
```

---

### Вариант 2: Стандартные карточки Home Assistant (Без сторонних плагинов)
Работает сразу на любой чистой установке Home Assistant:

```yaml
type: vertical-stack
cards:
  # Индикаторы нагрузки сервера
  - type: horizontal-stack
    cards:
      - type: gauge
        entity: sensor.3x_ui_server_cpu_usage
        name: CPU
        needle: true
        severity:
          green: 0
          yellow: 60
          red: 85
      - type: gauge
        entity: sensor.3x_ui_server_memory_usage
        name: RAM
        needle: true
        severity:
          green: 0
          yellow: 70
          red: 90
      - type: gauge
        entity: sensor.3x_ui_server_disk_usage
        name: Диск
        needle: true
        severity:
          green: 0
          yellow: 75
          red: 90

  # Список статусов и инбаундов
  - type: entities
    title: "Мониторинг 3x-ui"
    entities:
      - entity: binary_sensor.3x_ui_server_xray_core_status
        name: "Ядро Xray-core"
      - entity: sensor.3x_ui_server_total_clients
        name: "Всего клиентов"
      - entity: sensor.3x_ui_server_active_inbounds
        name: "Активных портов"
      - entity: sensor.3x_ui_server_total_download
        name: "Общий Download"
      - entity: sensor.3x_ui_server_total_upload
        name: "Общий Upload"
      - type: divider
      - entity: sensor.3x_ui_server_server_uptime
        name: "Аптайм сервера"
      - entity: sensor.3x_ui_server_tcp_connections
        name: "TCP Соединения"
      - entity: sensor.3x_ui_server_outbounds_configured
        name: "Настроено Аутбаундов"
```
