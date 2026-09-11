export const APP_VERSION = '1.0.4';

/**
 * @typedef {{ category?: { en: string; ru: string }; description: { en: string; ru: string } }} ChangeItem
 * @typedef {{ version: string; title?: { en: string; ru: string }; date?: string; type?: 'major' | 'minor' | 'patch'; changes: ChangeItem[] }} ChangelogEntry
 */

const CHANGELOG = [
  {
    version: '1.0.4',
    title: { en: 'Seeds & Plants, Combat Sync & Immediate Hit FX', ru: 'Семена и растения, синхронизация боя и мгновенные эффекты ударов' },
    date: '2026-09-11',
    type: 'minor',
    changes: [
      { category: { en: 'Seeds & Plants System', ru: 'Система семян и растений' }, description: {
        en: 'Full port of SPD seeds and plants: plants now grow on dungeon tiles, can be stepped on or triggered by thrown items/seeds, and produce unique tactical hazards and buffs (Firebloom, Icecap, Earthroot, Sorrowmoss, Starflower, Fadeleaf, Rotberry, Sungrass, Blindweed, Stormvine, Dreamfoil, Blandfruit Bush). Added plant inspection dialogs, dedicated state synchronizer, blooming particles, and audio.',
        ru: 'Полный порт семян и растений из SPD: растения теперь растут на клетках подземелья, активируются при наступлении или броске предметов/семян и вызывают уникальные тактические эффекты (Огнецвет, Ледоцвет, Землекорень, Тосноцвет, Звёздоцвет, Увядальник, Гнильягода, Солнцецвет, Слепоцвет, Вьюнок, Сноцвет, Куст бландфрута). Добавлены окна осмотра растений, отдельный синхронизатор состояния, частицы цветения и звуковые эффекты.',
      } },
      { category: { en: 'Combat & Cooldown Sync', ru: 'Бой и синхронизация кулдаунов' }, description: {
        en: 'Server-synchronized attack cooldowns (`next_attack_in_ms`) for melee and ranged attacks with client-side readiness tracking, preventing desynced actions. Removed artificial animation timeouts so damage numbers, blood splatters, and hit sparks trigger immediately upon hit confirmation.',
        ru: 'Синхронизация кулдаунов атак с сервером (`next_attack_in_ms`) для ближнего и дальнего боя с проверкой готовности на клиенте, предотвращающая рассинхрон действий. Убраны искусственные задержки анимаций, благодаря чему цифры урона, брызги крови и искры ударов отображаются мгновенно при подтверждении попадания.',
      } },
      { category: { en: 'Choice Dialog Delivery', ru: 'Доставка диалогов выбора' }, description: {
        en: 'Fixed delivery of subclass (Tengu\'s Mask) and armor ability (King\'s Crown) selection dialogs over WebSockets, ensuring prompts are reliably delivered on equip and re-emitted on reconnect.',
        ru: 'Исправлена доставка диалогов выбора подкласса (Маска Тенгу) и способности брони (Корона короля) через WebSocket — окна выбора гарантированно доставляются при экипировке и повторно отправляются при переподключении.',
      } },
      { category: { en: 'Talent Upgrades & UI Flow', ru: 'Прокачка талантов и интерфейс' }, description: {
        en: 'Streamlined talent upgrade workflow: particle bursts are now handled directly by the visual effects manager upon server confirmation (`TALENT_UPGRADED`), eliminating UI state lag and legacy tier-star DOM nodes.',
        ru: 'Оптимизирован поток прокачки талантов: вспышки частиц теперь запускаются менеджером визуальных эффектов напрямую при подтверждении от сервера (`TALENT_UPGRADED`), исключая задержки состояния UI и устаревшие элементы звёзд тиров.',
      } },
      { category: { en: 'Audio & Interactions', ru: 'Аудио и взаимодействия' }, description: {
        en: 'Added dedicated sound effect for locked doors and locked chests (`locked.mp3`).',
        ru: 'Добавлен отдельный звуковой эффект для запертых дверей и сундуков (`locked.mp3`).',
      } },
      { category: { en: 'Backend & Entity Cleanup', ru: 'Очистка бэкенда и сущностей' }, description: {
        en: 'Cleaned up backend entity hierarchies, item union types, scroll predicates, and unused code paths.',
        ru: 'Очищена иерархия сущностей бэкенда, объединения типов предметов, предикаты свитков и неиспользуемый код.',
      } },
    ],
  },
  {
    version: '1.0.2',
    title: { en: 'Optimizations & Server/Frontend Cleanup', ru: 'Оптимизации и очистка сервера/фронтенда' },
    date: '2026-09-06',
    type: 'patch',
    changes: [
      { description: {
        en: 'Merged the chore/optimizations PR: performance and code-quality improvements across the backend game engine and frontend, with expanded test coverage for audio events, bombs, boss pacing, crystal mimics, and talent mechanics.',
        ru: 'Слит PR chore/optimizations: улучшения производительности и качества кода в игровом движке бэкенда и на фронтенде, а также расширенное покрытие тестами аудио-событий, бомб, темпа боссов, кристальных мимиков и механик талантов.',
      } },
    ],
  },
  {
    version: '1.0.0',
    title: { en: 'Major Refactor: Event-Driven Architecture & OOP Engine', ru: 'Масштабный рефакторинг: событийная архитектура и ООП-движок' },
    date: '2026-09-01',
    type: 'major',
    changes: [
      { category: { en: 'Backend — Networking', ru: 'Бэкенд — Сеть' }, description: {
        en: 'Event-driven WebSocket architecture replacing the previous vibe-coded WS handling with a clean event-driven flow using WebSocketConnectionManager and MessageDispatcher.',
        ru: 'Событийная WebSocket-архитектура, заменяющая прежнюю неструктурированную обработку WS на чистый событийный поток с использованием WebSocketConnectionManager и MessageDispatcher.',
      } },
      { category: { en: 'Backend — Game Engine', ru: 'Бэкенд — Игровой движок' }, description: {
        en: 'OOP refactoring of game entities including Player, ItemBase (bombs, consumables, scrolls), and base entity classes into proper object-oriented structures.',
        ru: 'ООП-рефакторинг игровых сущностей: Player, ItemBase (бомбы, расходники, свитки) и базовые классы переведены в корректные объектно-ориентированные структуры.',
      } },
      { category: { en: 'Backend — Movement System', ru: 'Бэкенд — Система движения' }, description: {
        en: 'Complete movement system overhaul with new MovementController, block resolution logic, chest handling, and tick-based player movement.',
        ru: 'Полная переработка системы движения: новый MovementController, логика разрешения столкновений, обработка сундуков и пошаговое движение игрока.',
      } },
      { category: { en: 'Backend — Serialization', ru: 'Бэкенд — Сериализация' }, description: {
        en: 'Enhanced serialization for players, inventory items, and full game state persistence.',
        ru: 'Улучшенная сериализация игроков, предметов инвентаря и полное сохранение состояния игры.',
      } },
      { category: { en: 'Frontend — Input System', ru: 'Фронтенд — Система ввода' }, description: {
        en: 'New command-based input controller architecture with KeyActionRegistry, DirectionalMoveCommand, InventoryToggleCommand, QuickslotCommand, and more.',
        ru: 'Новая командно-ориентированная архитектура контроллера ввода: KeyActionRegistry, DirectionalMoveCommand, InventoryToggleCommand, QuickslotCommand и др.',
      } },
      { category: { en: 'Frontend — Movement Prediction', ru: 'Фронтенд — Предсказание движения' }, description: {
        en: 'Client-side movement prediction with new MovementPredictor and BlockerResolver for smooth player movement.',
        ru: 'Предсказание движения на стороне клиента: новые MovementPredictor и BlockerResolver для плавного перемещения игрока.',
      } },
      { category: { en: 'Frontend — Combat', ru: 'Фронтенд — Бой' }, description: {
        en: 'Major rewrite of combat events with proper state management and event-driven architecture.',
        ru: 'Крупная переработка боевых событий с корректным управлением состоянием и событийной архитектурой.',
      } },
      { category: { en: 'Frontend — Animation', ru: 'Фронтенд — Анимация' }, description: {
        en: 'New HeroAnimationPipeline for smooth character animations.',
        ru: 'Новый HeroAnimationPipeline для плавных анимаций персонажа.',
      } },
      { category: { en: 'Tests', ru: 'Тесты' }, description: {
        en: 'Comprehensive test coverage added for tick movement, inventory system, WS schemas, reconnect cleanup, no-echo events, per-player discovery, and admin tests.',
        ru: 'Добавлено всестороннее покрытие тестами: тиковое движение, инвентарь, WS-схемы, очистка при переподключении, события без эха, индивидуальное опознание и админ-тесты.',
      } },
    ],
  },
  {
    version: 'v0.18.0',
    title: { en: 'Plants, Pathfinding & Talent Rework', ru: 'Растения, прокладка пути и переработка талантов' },
    changes: [
      { description: {
        en: 'Plant mechanics and blandfruit fully ported from SPD: plants grow on tiles, can be triggered by movement or thrown seeds, and produce Blandfruit when cooked. Seed types include Firebloom, Icecap, Earthroot, Sorrowmoss, Starflower, Fadeleaf, Rotberry, and more — each with unique trigger effects.',
        ru: 'Механика растений и Бландфрут полностью перенесены из SPD: растения растут на клетках, срабатывают при движении или броске семян, и дают Бландфрут при готовке. Типы семян включают Огнецвет, Ледоцвет, Землекорень, Тосноцвет, Звёздоцвет, Увядальник, Гнильягоду и другие — каждый с уникальным эффектом срабатывания.',
      } },
      { description: {
        en: 'BFS pathfinding moved to the frontend: enemies are now avoided in path calculations, server-side MoveTo handler removed for a leaner movement pipeline.',
        ru: 'BFS-прокладка пути перенесена на фронтенд: враги теперь учитываются при расчёте маршрута, серверный обработчик MoveTo убран для более компактного пайплайна движения.',
      } },
      { description: {
        en: 'Client-side movement prediction with server reconciliation: your hero moves instantly on click while the server validates in the background, eliminating perceptible input lag.',
        ru: 'Предсказание движения на стороне клиента с согласованием на сервере: герой мгновенно перемещается по клику, а сервер валидирует в фоне — убирается ощутимая задержка ввода.',
      } },
      { description: {
        en: 'Mage talent rework: talent data split into enum definitions and runtime data, mob and movement logic extracted into separate packages for cleaner architecture.',
        ru: 'Переработка талантов мага: данные талантов разделены на определения enum и рантайм, логика мобов и движения вынесена в отдельные пакеты.',
      } },
      { description: {
        en: 'Tengu\'s Mask and King\'s Crown now grant subclass and armor ability choices on equip — re-emit pending choice windows on reconnect so players never miss the selection.',
        ru: 'Маска Тенгу и Корона короля теперь дают выбор подкласса и способности брони при экипировке — отложенные окна выбора повторно отправляются при переподключении.',
      } },
      { description: {
        en: 'Admin item browser with spawn popup: admins can browse all items, spawn them with a click, and cursed items now display their curse state visually.',
        ru: 'Обзор предметов админа со всплывающим окном спавна: админы могут просматривать все предметы, спавнить их одним кликом, проклятые предметы визуально отмечаются.',
      } },
      { description: {
        en: 'Item identification on hit: hitting an unidentified enemy has a chance to reveal its type, and curse identification events are now surfaced to the player.',
        ru: 'Опознание предметов при ударе: удар по неопознанному врагу с шансом раскрывает его тип, а события определения проклятия теперь отображаются игроку.',
      } },
      { description: {
        en: 'Feedback submissions via Telegram bot: players can send in-game feedback that posts directly to a configured Telegram chat.',
        ru: 'Отправка отзывов через Telegram-бот: игровые отзывы отправляются напрямую в настроенный чат Telegram.',
      } },
      { description: {
        en: 'Game loop optimized with concurrent WebSocket broadcasts and serialization caching — smoother tick delivery under high player counts.',
        ru: 'Оптимизация игрового цикла: параллельная рассылка WebSocket и кэширование сериализации — более плавная доставка тиков при большом количестве игроков.',
      } },
      { description: {
        en: 'Clicks now pass through the game log to the canvas when the chat panel is closed, so you never miss a movement command.',
        ru: 'Клики теперь проходят через игровой лог на canvas, когда панель чата закрыта — команды движения больше не блокируются.',
      } },
      { description: {
        en: 'Provoked Anger now correctly triggers on shield-break, matching SPD behavior.',
        ru: 'Провоцированная ярость теперь корректно срабатывает при разрушении щита (как в SPD).',
      } },
      { description: {
        en: 'Curse glyphs are hidden until the item is fully identified, preventing early curse disclosure.',
        ru: 'Глифы проклятия скрыты до полного опознания предмета, предотвращая раннее раскрытие проклятия.',
      } },
    ],
  },
  {
    version: 'v0.18.5',
    title: { en: 'Removed First Room Hidden Doors', ru: 'Убраны скрытые двери в первой комнате' },
    changes: [
      { description: {
        en: 'Entrance doors on floors 1 & 2 are no longer hidden on fresh games — they are now always visible from the start, matching a cleaner first-room experience.',
        ru: 'Входные двери на этажах 1 и 2 больше не скрыты при новой игре — они теперь всегда видны с самого начала, обеспечивая более чистый первый этаж.',
      } },
    ],
  },
  {
    version: 'v0.18.6',
    title: { en: 'Magical Sleep for Newly Spawned Mobs', ru: 'Магический сон для новых мобов' },
    changes: [
      { description: {
        en: 'Mobs spawned via the universal spawn system now enter a magical sleep state for 3 seconds before becoming active. They can be woken by taking damage or being alerted (combat system removes the buff and transitions AI to wandering).',
        ru: 'Мобы, спавняемые через универсальную систему спавна, теперь впадают в магический сон на 3 секунды перед активацией. Их можно разбудить, нанеся урон или привлекая внимание (система боя снимает бафф и переводит ИИ в блуждание).',
      } },
    ],
  },
  {
    version: 'v0.19.0',
    title: { en: 'Talent System Overhaul & Event Dispatcher Architecture', ru: 'Переработка системы талантов и событийная архитектура' },
    changes: [
      { category: { en: 'Backend — Talent System', ru: 'Бэкенд — Система талантов' }, description: {
        en: 'Complete talent system overhaul with a new registry-based architecture (`TalentEffectRegistry`, `EffectContext`). Handler modules for on_eat, on_kill, on_potion, on_step, passive stats, and rogue tick. New talents include Hearty Meal, Iron Stomach, Cashed Rations, Empowering Meal, Mystical Meal, Energizing Meal, Invigorating Meal, Cleave, Lethal Momentum, Soul Eater, and Deathly Durability.',
        ru: 'Полная переработка системы талантов с новой архитектурой на основе реестра (`TalentEffectRegistry`, `EffectContext`). Модули обработчиков для on_eat, on_kill, on_potion, on_step, пассивных статов и rogue_tick. Новые таланты: Сытный приём пищи, Железный желудок, Кэшированные паёки, Усиливающий приём пищи, Мистический приём пищи, Заряжающий приём пищи, Оживляющий приём пищи, Разрубание, Смертельный импульс, Пожиратель душ и Смертельная стойкость.',
      } },
      { category: { en: 'Backend — Player Tick', ru: 'Бэкенд — Тик игрока' }, description: {
        en: 'Major refactoring of `player_tick.py` with improved tick logic for player actions, movement validation, and interaction handling.',
        ru: 'Крупная переработка `player_tick.py` с улучшенной логикой тиков для действий игрока, валидации движения и обработки взаимодействий.',
      } },
      { category: { en: 'Backend — Movement & Chest', ru: 'Бэкенд — Движение и сундуки' }, description: {
        en: 'Enhanced `MovementController` with better block resolution and tick-based movement logic. Complete rewrite of chest handling (`chest.py`) with proper open/close state management and animation support.',
        ru: 'Улучшенный `MovementController` с лучшей логикой разрешения столкновений и пошаговым движением. Полная переработка обработки сундуков (`chest.py`) с корректным управлением состоянием открытия/закрытия и поддержкой анимации.',
      } },
      { category: { en: 'Backend — AI & Terrain', ru: 'Бэкенд — ИИ и ландшафт' }, description: {
        en: 'Updated Eye and Tengu AI behaviors for improved pathfinding and targeting. Blob overrides (Web, Key Ward, Light Wall, Eternal Fire) now correctly applied during terrain changes.',
        ru: 'Обновлено поведение ИИ Глаза и Тенгу для улучшенной навигации и целеуказания. Оверрайды блобов (Паутина, Ключевой страж, Световая стена, Вечный огонь) теперь корректно применяются при изменении ландшафта.',
      } },
      { category: { en: 'Frontend — Event Dispatcher', ru: 'Фронтенд — Диспетчер событий' }, description: {
        en: 'New `GameEventDispatcher` and `defaultEventDispatcher` for clean event-driven architecture replacing inline handlers. Events are now registered via factory functions (`createBossEventHandlers`, `createWorldEventHandlers`, etc.).',
        ru: 'Новый `GameEventDispatcher` и `defaultEventDispatcher` для чистой событийной архитектуры, заменяющей встроенные обработчики. События теперь регистрируются через фабричные функции.',
      } },
      { category: { en: 'Frontend — Window Manager', ru: 'Фронтенд — Менеджер окон' }, description: {
        en: 'Complete rewrite of window management with new `WindowManager` class supporting registration, level-based ordering, escape handling with fallback, and subscription-based updates.',
        ru: 'Полная переработка управления окнами с новым классом `WindowManager`, поддерживающим регистрацию, сортировку по уровням, обработку Escape и подписочные обновления.',
      } },
      { category: { en: 'Frontend — Services & Sync', ru: 'Фронтенд — Сервисы и синхронизация' }, description: {
        en: 'New centralized services (`EntityManager`, `GameCallbacks`, `HeroStateSync`, `VisualEffectsManager`, `WorldManager`). Dedicated synchronizers for Environment, Items, Mobs, Players, SelfPlayer, Traps, and Vision replacing the monolithic sync state approach.',
        ru: 'Новые централизованные сервисы. Специализированные синхронизаторы для окружения, предметов, мобов, игроков и т.д., заменяющие монолитный подход к синхронизации состояния.',
      } },
      { category: { en: 'Frontend — Animation & Rendering', ru: 'Фронтенд — Анимация и рендеринг' }, description: {
        en: 'New `ItemAnimationManager` for handling item animations with proper lifecycle management. Enhanced trap rendering system with new visual effects.',
        ru: 'Новый `ItemAnimationManager` для управления анимациями предметов с корректным жизненным циклом. Улучшенная система рендеринга ловушек с новыми визуальными эффектами.',
      } },
      { category: { en: 'Frontend — Combat & Talents', ru: 'Фронтенд — Бой и таланты' }, description: {
        en: 'Major rewrite of combat events with proper state management. New talent query hooks (`useTalentData`, `useTalentUI`, `useTalents`) replacing the old `useTalentFlow` system.',
        ru: 'Крупная переработка боевых событий с корректным управлением состоянием. Новые хуки для талантов, заменяющие старую систему.',
      } },
      { category: { en: 'Tests', ru: 'Тесты' }, description: {
        en: 'Added tests for universal spawns (magical sleep), talent registry, tick movement, audio events, bombs, boss pacing, crystal mimic runtime, rest regen, scrolls, sewers runtime, and domain services.',
        ru: 'Добавлены тесты для универсального спавна (магический сон), реестра талантов, тикового движения, аудио-событий, бомб, темпа боссов, кристальных мимиков, восстановления после отдыха, свитков, канализации и доменных сервисов.',
      } },
    ],
  },
  {
    version: 'v0.14.0',
    title: { en: 'Global & Direct Chat', ru: 'Глобальный и ближний чат' },
    changes: [
      { description: {
        en: 'New in-game chat: press Enter to open the chat bar. The Global channel (default) reaches every player across all floors.',
        ru: 'Новый чат в игре: нажмите Enter, чтобы открыть строку ввода. Глобальный канал (по умолчанию) виден всем игрокам на всех этажах.',
      } },
      { description: {
        en: 'Direct channel: click the G/D buttons next to the chat bar to switch. Direct messages are proximity-based — only players on the same floor with line of sight to you receive them.',
        ru: 'Ближний канал: переключение кнопками G/D рядом с строкой ввода. Сообщения ближнего канала видны только игрокам на том же этаже, у которых есть прямая видимость на вас.',
      } },
      { description: {
        en: 'Anti-spam: 1 global message per 10 seconds and 10 direct messages per 10 seconds. Exceeding the limit shows a warning toast instead of sending.',
        ru: 'Защита от спама: 1 глобальное сообщение за 10 секунд и 10 ближних сообщений за 10 секунд. Превышение лимита показывает предупреждающее сообщение вместо отправки.',
      } },
      { description: {
        en: 'Sending a message instantly closes the chat bar and pops a speech bubble above your hero\'s head — and above nearby players when they talk.',
        ru: 'После отправки строка ввода мгновенно закрывается, а над головой вашего героя появляется облачко с текстом — оно также появляется у говорящих рядом игроков.',
      } },
    ],
  },
  {
    version: 'v0.13.0',
    title: { en: 'XP Sharing, Rest Healing & Skeleton Key Overhaul', ru: 'Обмен опытом, отдых и ключ скелета' },
    changes: [
      { description: {
        en: 'Party XP sharing: the killer earns a mob\'s full EXP and every other alive hero on the same floor earns half (rounded up) — solo play is unchanged.',
        ru: 'Распределение опыта: убийца получает полный опыт моба, а каждый живой герой на этом же этаже — половину (с округлением вверх). В одиночной игре всё без изменений.',
      } },
      { description: {
        en: 'Passive rest regeneration: while standing still with no hostile mob within 5 tiles, you now regenerate 1 HP every 3 seconds, so you can recover after clearing a room.',
        ru: 'Пассивное восстановление: стоя на месте без враждебных мобов в радиусе 5 клеток, герой восстанавливает 1 ОЗ каждые 3 секунды — можно отдохнуть после зачистки комнаты.',
      } },
      { description: {
        en: 'New Nourished buff from eating any food: it doubles the rest-healing rate and keeps a reduced heal ticking even during combat; duration scales with the food\'s energy value.',
        ru: 'Новый бафф «Сытость» после любой еды: удваивает скорость восстановления от отдыха и даёт уменьшенное лечение даже во время боя; длительность зависит от питательности еды.',
      } },
      { description: {
        en: 'Emergency heal prompt: at 20% HP or below with a Health Potion or a filled Waterskin on hand, a prompt appears (with a warning sound) — press Space to drink it instantly.',
        ru: 'Срочная помощь: при 20% ОЗ и ниже, если под рукой есть зелье здоровья или фляга с водой, появляется подсказка (со звуком предупреждения) — нажмите Пробел, чтобы мгновенно выпить.',
      } },
      { description: {
        en: 'Surprise attacks after breaking line of sight: a mob that loses sight of you and then sees you again is surprised for 2 seconds, so your strikes land as surprise attacks (auto-hit + crit) — matching SPD\'s stale-enemySeen rule.',
        ru: 'Внезапные атаки после разрыва обзора: моб, который потерял вас из виду, а затем снова увидел, уязвим в течение 2 секунд — ваши удары становятся внезапными (авто-попадание + крит), как в оригинале SPD.',
      } },
      { description: {
        en: 'Hero window rework: Stats, Talents and Buffs are now one tabbed window, opened from the avatar, the `t` key, or the level-up banner. The Talents tab embeds the full upgrade pane, and `t`/Escape toggle or close it cleanly.',
        ru: 'Переработанное окно героя: характеристики, таланты и баффы объединены в одно окно с вкладками (клик по аватару, клавиша T или баннер уровня); вкладка талантов содержит полную панель прокачки, а T/Escape корректно переключают и закрывают его.',
      } },
      { description: {
        en: 'Examining another player now shows their class, level and STR.',
        ru: 'Осмотр другого игрока теперь показывает его класс, уровень и силу.',
      } },
      { description: {
        en: 'Two-phase unlocking: using a key spends it immediately and blocks input, but the door or chest visibly opens at the end of the ~0.5s operate animation — with the unlock sound landing there instead of on the bump. Doorways and chests can no longer be double-unlocked by two players at once.',
        ru: 'Двухфазное открывание: использование ключа сразу тратит его и блокирует действие, но дверь/сундук видимо открываются в конце анимации (~0,5 с) со звуком открывания, а не при прикосновении. Двери и сундуки больше нельзя открыть вдвоём одновременно.',
      } },
      { description: {
        en: 'Skeleton Key overhaul (full SPD port): unlock iron doors (1 charge), crystal doors (5) and hero-locked doors (free), lock ordinary doors with your own key (2 charges), open locked/crystal chests (2/5 charges), or summon a temporary key wall at distant targets (10s). Charge cap now scales with level (3 + level/2), the key renders with its real sprite, and the inventory shows its charge readout.',
        ru: 'Переработка Ключа скелета (полный порт SPD): открытие железных дверей (1 заряд), кристальных дверей (5) и дверей, запертых героем (бесплатно), запирание обычных дверей своим ключом (2 заряда), открытие запертых/кристальных сундуков (2/5 зарядов) или призыв временной ключевой стены по дальней цели (10 с). Максимум заряда растёт с уровнем (3 + уровень/2), ключ отображается со своим спрайтом, а в инвентаре виден его заряд.',
      } },
      { description: {
        en: 'Hero-locked doors: a door you lock with the Skeleton Key renders like a locked door and refuses to open by bump while a non-cursed key is equipped (SPD match).',
        ru: 'Двери, запертые героем: дверь, запертая Ключом скелета, отображается как запертая и не открывается ударом, пока надет непроклятый ключ (как в SPD).',
      } },
      { description: {
        en: 'Per-player identification: potions, scrolls and rings now reveal their real type only to the hero who personally discovered them this run — other players still see the scrambled label. Shared mechanics (recipes, shop prices) remain party-wide.',
        ru: 'Опознание теперь индивидуальное: зелья, свитки и кольца показывают свой настоящий тип только герою, лично опознавшему их в этом забеге — остальные игроки видят перемешанную этикетку. Общие механики (рецепты, цены магазина) остаются командными.',
      } },
      { description: {
        en: 'Search reveal for teammates: the search sweep effect now plays for any player in line-of-sight of the searcher, not just the searcher.',
        ru: 'Поиск виден союзникам: эффект обыска теперь воспроизводится у всех игроков в прямой видимости ищущего, а не только у него самого.',
      } },
      { description: {
        en: 'Lost Backpack recovery: weapon, armor and artifact are re-equipped automatically when their slot is empty, and the Waterskin is recovered whole (volume intact) instead of turning into dewdrops.',
        ru: 'Возврат Потерянного рюкзака: оружие, броня и артефакт автоматически экипируются, если слот пуст, а фляга с водой возвращается целиком (с сохранённым объёмом) вместо превращения в капли росы.',
      } },
      { description: {
        en: 'Audio fixes: merchant buy/sell plays the gold sound (was a generic click), dropped potions no longer play the shatter sound, and the unlock sound only fires when a door/chest actually opens — not when a chest merely spawns.',
        ru: 'Исправления звука: покупка/продажа у торговца играет звук золота (вместо обычного клика), брошенные зелья больше не играют звук разбития при броске, а звук открывания звучит только когда дверь/сундук действительно открываются, а не при появлении сундука.',
      } },
      { description: {
        en: 'Sad Ghost reward icons scaled down to fit the window properly.',
        ru: 'Иконки наград Призрака уменьшены, чтобы корректно помещаться в окно.',
      } },
      { description: {
        en: 'Desktop inventory now renders the bag grid in two rows.',
        ru: 'Инвентарь на десктопе теперь отображает сумку в два ряда.',
      } },
      { description: {
        en: 'Custom cursor enlarged to roughly 2x for better visibility.',
        ru: 'Пользовательский курсор увеличен примерно вдвое для лучшей видимости.',
      } },
      { description: {
        en: 'Admin fixes: admin gold spawning works correctly, the admin item browser closes with Escape, and picking up potions/scrolls as admin identifies them immediately.',
        ru: 'Исправления для админа: спавн золота работает корректно, обзор предметов закрывается по Escape, а подбор зелий/свитков админом мгновенно их опознаёт.',
      } },
      { description: {
        en: 'Removed the Wait button from the toolbar — resting is now handled automatically via the new passive regeneration.',
        ru: 'Кнопка «Подождать» убрана с панели инструментов — отдых теперь работает автоматически благодаря новому пассивному восстановлению.',
      } },
    ],
  },
  {
    version: 'v0.12.0',
    title: { en: 'Release Automation & Docs', ru: 'Релизная автоматизация и документация' },
    changes: [
      { description: {
        en: 'New release flow: pushing to main now automatically creates a GitHub release with the current version.',
        ru: 'Новый процесс релиза: при пуше в main автоматически создаётся GitHub release с текущей версией.',
      } },
      { description: {
        en: 'README rewritten with a full feature list, badges, and the correct play link.',
        ru: 'README переписан: полный список фич, бейджи и правильная ссылка на игру.',
      } },
    ],
  },
  {
    version: 'v0.11.0',
    title: { en: 'Auto Versioning', ru: 'Автообновление версии' },
    changes: [
      { description: {
        en: 'The game version is now bumped automatically by a pre-commit git hook (minor for features, patch for fixes), so it always matches the latest changes.',
        ru: 'Версия игры теперь обновляется автоматически pre-commit git-хуком (минорная для фич, патч для исправлений), так что она всегда соответствует последним изменениям.',
      } },
    ],
  },
  {
    version: 'v0.10.3',
    title: { en: 'Cursed Wand, Stagger & Wand Overhaul', ru: 'Проклятый посох, дезориентация и обновление посохов' },
    changes: [
      { description: {
        en: 'Cursed Wand overhaul: 32 effects across 4 weighted tiers (was ~10 basic effects). New effects include forest fire, golden mimic summon, hero shape shift, super nova, sinkhole, gravity chaos, sheep polymorph, and more. Wondrous Resin trinket restricts pool to positive-only effects.',
        ru: 'Переработка Проклятого посоха: 32 эффекта в 4 взвешенных категориях (было ~10 базовых). Новые эффекты включают лесной пожар, призыв золотого мимика, превращение героя, суперновую, провал и хаос гравитации.',
      } },
      { description: {
        en: 'New Stagger status effect: applied by Wand of Blast Wave wall-slam. Staggered entities cannot move or attack, and GreatCrab\'s shell defense drops while staggered — opening a window for wand damage.',
        ru: 'Новый эффект дезориентации: применяется Посохом взрывной волны при ударе о стену. Дезориентированные существа не могут двигаться или атаковать, а панцирь Краба-гиганта падает при дезориентации — открывая окно для атак посохами.',
      } },
      { description: {
        en: 'Piercing beams: Wand of Death Ray now fires a piercing beam that passes through characters and walls, with range scaling based on wand level.',
        ru: 'Пронизывающие лучи: Посох смерти луча теперь стреляет пронизывающим лучом, проходящим через существ и стены, с дальностью, масштабирующейся от уровня посоха.',
      } },
      { description: {
        en: 'Cursed wand zaps: zapping a cursed wand now triggers a random cursed effect (rainbow bolt visual + ZAP sound) instead of the wand\'s normal effect, and the curse becomes known.',
        ru: 'Проклятые посохи: применение проклятого посоха теперь вызывает случайный проклятый эффект (радужный визуал + звук ZAP) вместо обычного эффекта, и проклятие становится известным.',
      } },
      { description: {
        en: 'Per-wand impact sounds: frost bolts play SHATTER, force bolts play BLAST, corrosion bolts play GAS, earth/shadow bolts play HIT_MAGIC.',
        ru: 'Звуки ударов по посохам: ледяные болты воспроизводят SHATTER, силовые болты — BLAST, коррозионные — GAS, земляные/теневые — HIT_MAGIC.',
      } },
      { description: {
        en: 'Staff imbued wand charge fix: max charges now correctly calculated as base + level (was base + level + 1).',
        ru: 'Исправление зарядов посоха с встроенным посохом: максимум зарядов теперь корректно рассчитывается как база + уровень (было база + уровень + 1).',
      } },
      { description: {
        en: 'Rogue\'s Cloak of Shadows is now placed in the Lost Backpack on death instead of being permanently deleted. Items recovered from the backpack are auto-assigned to empty quick slots.',
        ru: 'Плащ Теней разбойника теперь помещается в Потерянный рюкзак при смерти вместо навсегда удаления. Предметы из рюкзака автоматически назначаются в пустые быстрые слоты.',
      } },
      { description: {
        en: 'Server stability: per-message try/except prevents one malformed WebSocket message from crashing the entire connection.',
        ru: 'Стабильность сервера: блок try/except на каждое сообщение предотвращает краш всего WebSocket-подключения из-за одного некорректного сообщения.',
      } },
      { description: {
        en: 'New event types: PUSH, SUMMON, ZAP, CORRUPTED, CURSED_WAND_STUB, TERRAIN_CHANGE, ITEM_DROP, LIGHTNING_ARC.',
        ru: 'Новые типы событий: PUSH, SUMMON, ZAP, CORRUPTED, CURSED_WAND_STUB, TERRAIN_CHANGE, ITEM_DROP, LIGHTNING_ARC.',
      } },
      { description: {
        en: 'Mob respawn nerfed at higher floors: per-floor mob limit capped at 12 (was unlimited, e.g. 30 on floor 25), and respawn cooldown now scales with depth (50 + floor_id × 3 ticks, up from flat 50). Applies to both public and private rooms.',
        ru: 'Нерф спавна мобов на высоких этажах: лимит мобов на этаж ограничен 12 (был неограничен, напр. 30 на этаже 25), кулдаун спавна масштабируется с глубиной (50 + floor_id × 3 тиков вместо фиксированных 50). Применяется к публичным и приватным комнатам.',
      } },
      { description: {
        en: 'DM-100 now fires its electric zap at range (was silently falling back to melee only) — a cyan lightning bolt up to 8 tiles away that bypasses armor DR, matching the original.',
        ru: 'DM-100 теперь стреляет электрическим разрядом на дистанции (раньше молча переходил в ближний бой) — голубая молния до 8 клеток, игнорирующая броню, как в оригинале.',
      } },
      { description: {
        en: 'Guard\'s chain-pull reworked to match the original: it now drags a distant (2-4 tile, line-of-sight) target toward itself along the chain and Cripples them, once per Guard — instead of just waking every mob on the floor.',
        ru: 'Рывок цепью Стража переработан по оригиналу: теперь он подтягивает удалённую (2-4 клетки, в прямой видимости) цель к себе по цепи и накладывает Хромоту, один раз за Стража — вместо пробуждения всех мобов на этаже.',
      } },
      { description: {
        en: 'Ethereal Chains artifact and Guard\'s chain-pull now render an actual chain effect (rattling line + sound) between puller and target; both previously fired with no visual or audio at all.',
        ru: 'Артефакт «Эфирные цепи» и рывок цепью Стража теперь отображают настоящий эффект цепи (звенящая линия + звук) между тянущим и целью; раньше оба срабатывали без визуала и звука.',
      } },
      { description: {
        en: 'Fixed stale collision/line-of-sight data after terrain changes: destroying walls (Eye\'s death gaze, Wand of Disintegration), growing plants (Wand of Regrowth), and cursed-wand terrain effects now immediately rebuild the floor\'s passable/solid/LOS grid instead of leaving it stale until the next area transition. Blob-based overrides (Web, Key Ward, Light Wall, Eternal Fire) are now correctly applied too, and traps are marked avoid-but-walkable so pathing routes around them without blocking players.',
        ru: 'Исправлены устаревшие данные проходимости/видимости после изменения ландшафта: разрушение стен (взгляд смерти Глаза, Посох дезинтеграции), выращивание растений (Посох роста) и эффекты проклятых посохов теперь сразу пересчитывают сетку проходимости/твёрдости/видимости этажа, а не оставляют её устаревшей до следующего перехода между зонами. Оверрайды от блобов (Паутина, Ключевой страж, Световая стена, Вечный огонь) теперь тоже применяются корректно, а ловушки помечены как «избегаемые, но проходимые» — путь строится в обход них, но игроков они не блокируют.',
      } },
      { description: {
        en: 'Fixed the Cursed Wand\'s Sinkhole effect creating a shallow pit instead of an actual fall-through chasm.',
        ru: 'Исправлен эффект «Провал» проклятого посоха: теперь создаёт настоящую пропасть, в которую можно провалиться, а не мелкую яму.',
      } },
      { description: {
        en: 'Guard\'s armor drop now gets 3x rarer each time one drops (matching the original\'s diminishing-return loot rule), instead of always rolling the same chance.',
        ru: 'Шанс выпадения брони со Стража теперь падает втрое с каждым выпадением (как в оригинале), а не остаётся постоянным.',
      } },
      { description: {
        en: 'Fixed Wand of Prismatic Light never actually marking terrain as explored when revealing hidden areas.',
        ru: 'Исправлен Посох радужного света: раскрытие территории больше не проходит впустую — открытые клетки теперь действительно помечаются исследованными.',
      } },
      { description: {
        en: 'Guide Page floor items no longer keep spawning once the party has found every Adventurer\'s Guide page — they used to appear guaranteed on every floor from depth 5 onward and could never be picked up, leaving permanent clutter.',
        ru: 'Страницы путеводителя больше не появляются на полу, если отряд уже нашёл все страницы — раньше они гарантированно возникали на каждом этаже с 5-го и ниже и никогда не подбирались, засоряя пол навсегда.',
      } },
      { description: {
        en: 'Discovering a new Adventurer\'s Guide page now plays a sound and shows a message; it previously happened silently with no feedback at all.',
        ru: 'Обнаружение новой страницы путеводителя теперь сопровождается звуком и сообщением; раньше это происходило совершенно незаметно.',
      } },
      { description: {
        en: 'Sacrifice room fully implemented: the pedestal now renders as its own tile instead of plain floor, blue sacrificial fire particles continuously rise from the 3x3 ember pit, and mob sacrifices trigger visual/audio feedback — blue particle burst on feed, massive blue burst across all 9 cells when the fire is consumed and the prize drops.',
        ru: 'Комната жертвы полностью реализована: пьедестал теперь отображается как отдельный тайл вместо обычного пола, голубые огоньки жертвенного огня непрерывно поднимаются из ямы из углей 3×3, а жертвоприношения мобов сопровождаются визуальной и звуковой обратной связью — взрыв голубых частиц при кормлении огня, мощный голубой взрыв на всех 9 клетках, когда огонь поглощён и выпадает награда.',
      } },
      { description: {
        en: 'Chasm-fall prompt no longer requires Escape to dismiss: pressing a movement key now closes it too, and closing it (by any method) suppresses the prompt from popping up again for 2 seconds so bumping the ledge again doesn\'t instantly reopen it.',
        ru: 'Диалог прыжка в пропасть больше не требует Escape для закрытия: клавиша движения тоже его закрывает, а после закрытия (любым способом) диалог не появляется повторно 2 секунды, чтобы повторный подход к краю не открывал его мгновенно снова.',
      } },
      { description: {
        en: 'Food can actually be eaten now: Ration, Pasty, Mystery Meat and the rest were missing the Eat action from their menu entirely, leaving only Throw/Drop.',
        ru: 'Еду теперь действительно можно съесть: у Пайка, Пирожка, Таинственного мяса и остальных продуктов в меню полностью отсутствовало действие «Съесть», оставались только Бросить/Выбросить.',
      } },
      { description: {
        en: 'Eating now gives real feedback: a message, the original game\'s eat sound (previously silent), and the same busy animation drinking/reading already had.',
        ru: 'Поедание еды теперь даёт настоящую обратную связь: сообщение, оригинальный звук поедания (раньше было беззвучно) и ту же анимацию занятости, что уже есть у питья/чтения.',
      } },
      { description: {
        en: 'Fixed invisible buffs from eating: Barkskin (Frozen Carpaccio, Phantom Meat) and Roots (unlucky Mystery Meat) now show a buff icon like every other effect, instead of applying with no visual feedback at all.',
        ru: 'Исправлены невидимые баффы от еды: Кора (Замороженное мясо, Мясо призрака) и Корни (неудачное Таинственное мясо) теперь показывают иконку баффа, как и все остальные эффекты, а раньше применялись вообще без какой-либо визуальной обратной связи.',
      } },
      { description: {
        en: 'Well Fed (from Meat Pie) now matches the original: +1 HP every 18 seconds for 450 seconds, instead of a flat 3x regen-speed boost for 50 seconds. Supply Ration also plays the original\'s cosmetic energy-burst effect when it tops up a worn Cloak of Shadows.',
        ru: 'Сытость (от Мясного пирога) теперь соответствует оригиналу: +1 к здоровью каждые 18 секунд в течение 450 секунд вместо ускорения регенерации в 3 раза на 50 секунд. Паёк снабжения также воспроизводит оригинальный косметический эффект всплеска энергии при подзарядке надетого Плаща теней.',
      } },
      { description: {
        en: '11 new traps implemented and wired in: Alarm (wakes the floor), Summoning/Distortion (spawn ambushing mobs), Teleportation/Gateway/Warping (scatter or bunch up everyone nearby), Flashing (bleed, blind, cripple), Disarming (steals your weapon or destroys a Statue), Cursing (curses your gear), Grim (heavy single-target hit) and Guardian (spawns hunting Statues on deep floors). Previously these all silently fell back to a flat 2 damage tick with none of their named effect.',
        ru: 'Реализованы и подключены 11 новых ловушек: Тревога (будит этаж), Призыв/Искажение (призывают мобов из засады), Телепортация/Портал/Искривление (раскидывают или собирают всех рядом), Ослепление (кровотечение, слепота, паралич ног), Обезоруживание (крадёт оружие или уничтожает Статую), Проклятие (проклинает снаряжение), Мрачная (мощный удар по одной цели) и Страж (призывает преследующих Статуй на глубоких этажах). Раньше все они незаметно откатывались к фиксированному урону в 2 единицы без какого-либо из заявленных эффектов.',
      } },
      { description: {
        en: 'Death now consolidates every dropped item into a single owner-only Lost Backpack instead of scattering it on the ground — previously only the Rogue\'s Cloak of Shadows got that treatment. Bags stay on the player, and items that were quickslotted before death are now re-seated to their exact original slot on recovery instead of just filling the first empty one.',
        ru: 'Смерть теперь собирает все выпавшие предметы в единственный доступный только владельцу Потерянный рюкзак вместо того, чтобы разбрасывать их по полу — раньше так поступали только с Плащом теней разбойника. Сумки остаются у игрока, а предметы, привязанные к быстрым слотам до смерти, теперь при находке возвращаются в тот же самый слот, а не просто в первый свободный.',
      } },
      { description: {
        en: 'Fixed periodic mob respawns on Caves/City/Halls (floor 11+) silently spawning nothing but Rats; they now draw from the correct region\'s mob pool, same as initial floor population already did.',
        ru: 'Исправлено: периодическое возрождение мобов на Пещерах/Городе/Чертогах (этаж 11+) незаметно порождало только Крыс; теперь используется правильный региональный пул мобов, как и при первоначальном заселении этажа.',
      } },
      { description: {
        en: 'Fixed the buff icon row floating disconnected above the HP bar in desktop mode; it\'s now anchored just above it like the rest of the status pane.',
        ru: 'Исправлено: ряд иконок баффов в десктопном режиме «плавал» в воздухе над полосой здоровья, оторванный от панели; теперь он закреплён прямо над ней, как и остальная часть панели.',
      } },
      { description: {
        en: 'Fixed the game viewport getting stuck at its initial size: resizing the window (or rotating a tablet) after entering a run no longer freezes the desktop/mobile layout at whatever size the window was when you loaded the page.',
        ru: 'Исправлено зависание размера игрового окна: изменение размера окна (или поворот планшета) после входа в подземелье больше не замораживает десктопный/мобильный макет в том размере, что был при загрузке страницы.',
      } },
    ],
  },
  {
    version: 'v0.10.2',
    title: { en: 'Respawn & Backpack Visibility Fix', ru: 'Исправление возрождения и видимости рюкзака' },
    changes: [
      { description: {
        en: 'Difficulty-based respawns restored: Easy and Normal players get 3 free in-place respawns (50% HP, debuffs cleared, spawn protection). Boss-floor deaths are final. This was accidentally removed in the ankh system update.',
        ru: 'Возвращено возрождение, зависящее от сложности: на лёгком и среднем уровнях игроки получают 3 бесплатных возрождения на месте (50% HP, баффы сняты, защита спавна). Гибель на этажах боссов окончательна. Эта механика была случайно удалена при обновлении системы Анкх.',
      } },
      { description: {
        en: 'Lost Backpack is now only visible to the player who dropped it — other players cannot see or loot another player\'s death backpack.',
        ru: 'Потерянный рюкзак теперь виден только игроку, потерявшего его — другие игроки не могут увидеть или забрать чужой рюкзак смерти.',
      } },
    ],
  },
  {
    version: 'v0.10.1',
    title: { en: 'Fire Visuals & Audio Fix', ru: 'Огонь: визуал и звук' },
    changes: [
      { description: {
        en: 'Fixed status effect particles (burning, frozen, chilled, bleeding, levitation) being wiped every server tick — burning entities are now visibly wreathed in flames, with a flickering heat halo and rising embers.',
        ru: 'Исправлены частицы статус-эффектов (горение, заморозка, озноб, кровотечение, левитация), стиравшиеся каждый тик сервера — горящие существа теперь видимо объяты пламенем, с мерцающим жаровым ореолом и поднимающимися искрами.',
      } },
      { description: {
        en: 'Fire fields finally look like fire: burning tiles glow with flickering orange light, flame particles are larger with yellow-hot cores, and flames spawn across whole tiles instead of only at cell centers.',
        ru: 'Огненные поля наконец выглядят как огонь: горящие клетки мерцают оранжевым светом, частицы пламени стали крупнее с раскалёнными жёлтыми ядрами и появляются по всей клетке, а не только в её центре.',
      } },
      { description: {
        en: 'Fire audio: the burning sound (preloaded but never actually played) now plays on ignitions, liquid flame potions, firebombs, burning/blazing traps, Wand of Fireblast hits, fire imbue, and sacrificial fire — capped to one play per second so mass ignitions don\'t machine-gun the sound.',
        ru: 'Звук огня: звук горения (был загружен, но никогда не играл) теперь звучит при поджоге, зелье жидкого пламени, огненных бомбах, огненных/пламенных ловушках, попаданиях Жезла огненного взрыва, огненного зачарования и жертвенного огня — ограничен одним воспроизведением в секунду, чтобы массовые поджоги не превращались в трескотню.',
      } },
      { description: {
        en: 'Flame bursts now rise like real fire instead of falling downward.',
        ru: 'Вспышки пламени теперь поднимаются вверх, как настоящий огонь, а не падают вниз.',
      } },
    ],
  },
  {
    version: 'v0.10.0',
    title: { en: 'Ankh Resurrection & Adventurer\'s Guide', ru: 'Возрождение Анкх и Путеводитель искателя' },
    changes: [
      { description: {
        en: 'New animated main menu: scrolling parallax background, banner with pulsing glow, and two flickering torches — ported from the original Shattered Pixel Dungeon title screen.',
        ru: 'Новое анимированное главное меню: прокручивающийся параллакс-фон, баннер с пульсирующим свечением и два мерцающих факела.',
      } },
      { description: {
        en: 'Added Settings (audio + display), Changes, Guide, About, Rankings and News screens.',
        ru: 'Добавлены экраны настроек (аудио + экран), изменений, гайда, об игре, рейтингов и новостей.',
      } },
      { description: {
        en: 'Audio now has independent music and SFX volume controls plus a master mute.',
        ru: 'Аудио с независимыми регуляторами музыки и звуковых эффектов, плюс общее отключение звука.',
      } },
      { description: {
        en: 'Display option to toggle background animations.',
        ru: 'Опция экрана для переключения фоновой анимации.',
      } },
      { description: {
        en: 'Shop rooms now stock 19 items (up from 18). New sprites added for Ankh, Lost Backpack, Dwarf Token, and all food variants. Guide panel completely rewritten with paginated SPD-style content.',
        ru: 'Магазины теперь продают 19 товаров (было 18). Новые спрайты для Анх, Потерянного рюкзака, Жетона гномов и всех вариантов еды. Панель справки полностью переписана с постраничным SPD-стилем.',
      } },
    ],
  },
  {
    version: 'v0.9.0',
    title: { en: 'Public Room Replenishment & Chat', ru: 'Пополнение публичной комнаты и чат' },
    changes: [
      { description: {
        en: 'Public room keeps repopulating: floor items respawn in waves on empty tiles (base 2 + 1 per active player, roughly every 5s) so late joiners can still find loot, and defeated bosses come back after a ~30s cooldown so new players get a shot at the fight; looted chests respawn too (~20s).',
        ru: 'Публичная комната теперь сама пополняется: предметы на этажах волнами появляются на свободных клетках (2 базово + 1 за каждого активного игрока, примерно раз в 5с), поэтому опоздавшие игроки всё ещё находят добычу; побеждённые боссы возвращаются через ~30с, давая шанс новым игрокам сразиться с ними; открытые сундуки тоже восстанавливаются (~20с).',
      } },
      { description: {
        en: 'Mob respawns are now blocked on every boss floor (5, 10, 15, 20, 25), not just floor 1; the public room\'s regular mob respawn timer also runs 25% faster than solo/private games.',
        ru: 'Возрождение мобов теперь заблокировано на всех этажах боссов (5, 10, 15, 20, 25), а не только на первом; в публичной комнате обычный таймер возрождения мобов также работает на 25% быстрее, чем в одиночных/приватных играх.',
      } },
      { description: {
        en: 'Chat now shows join/leave messages ("X joined the game." / "X left the game.") and boss-kill announcements in the public room.',
        ru: 'В чате теперь показываются сообщения о входе/выходе игроков («X присоединился к игре.» / «X покинул игру.») и объявления о гибели боссов в публичной комнате.',
      } },
      { description: {
        en: 'Fixed the ghost sewer quest\'s tense music continuing to play after the quest boss died; it now cuts back to the ambient track immediately instead of waiting for the reward to be claimed.',
        ru: 'Исправлена ошибка, из-за которой напряжённая музыка призрачного квеста в канализации продолжала играть после гибели босса квеста; теперь она сразу переключается на фоновую композицию, не дожидаясь получения награды.',
      } },
      { description: {
        en: 'Rendering fixes: Sentry mobs now draw their sprite, the Statue floor prop no longer looks cropped/floating (wrong atlas offset), the floor picker dropdown opens downward instead of off-screen upward, and the boss-slain banner/badge moved higher so it doesn\'t sit on top of the HUD.',
        ru: 'Исправления отрисовки: моб Стражник (Sentry) теперь отображается со спрайтом, декорация-статуя больше не выглядит обрезанной/парящей (было неверное смещение в атласе), выпадающий список выбора этажа теперь открывается вниз вместо того, чтобы уходить за экран вверх, а баннер/значок гибели босса подняты выше, чтобы не перекрывать HUD.',
      } },
    ],
  },
  {
    version: 'v0.8.2',
    title: { en: 'Room Selection, Shop & Mimic Fixes', ru: 'Выбор комнаты, исправления магазина и мимиков' },
    changes: [
      { description: {
        en: 'Fixed equipped-armor rendering on other players: the correct sprite-sheet row is now picked from the item\'s armor tier, and a row-height bug (16px vs the actual 15px stride) that misaligned the sprite is fixed.',
        ru: 'Исправлен рендер брони на других игроках — теперь корректно выбирается строка спрайт-листа по уровню брони, и исправлена ошибка высоты строки (было 16px вместо реальных 15px), из-за которой спрайт съезжал.',
      } },
      { description: {
        en: 'Added room selection to the main menu: join the public room or create/join a named private group (with an optional password), and see how many players are active before you commit.',
        ru: 'В главном меню появился выбор комнаты: можно зайти в публичную комнату или создать/присоединиться к именованной приватной группе (с необязательным паролем) и увидеть число активных игроков перед входом.',
      } },
      { description: {
        en: 'Shop stock is now listed in full regardless of your distance from the shopkeeper (previously only items within 1 tile showed up); Velvet Pouch and Waterskin can no longer be sold for gold.',
        ru: 'Список товаров в магазине теперь полностью отображается независимо от расстояния до торговца (раньше показывались только предметы в радиусе 1 клетки); Бархатный мешочек и Флягу для воды больше нельзя продать за золото.',
      } },
      { description: {
        en: 'Disguised Mimics (regular, Golden, Ebony) now properly reveal themselves — burst out, play their sound, and start hunting — when their fake chest is opened, instead of behaving like an ordinary chest; fixed potion spawn rates.',
        ru: 'Замаскированные мимики (обычный, золотой, эбеновый) теперь корректно раскрываются — выпрыгивают, издают звук и начинают охоту — при открытии их поддельного сундука, вместо того чтобы вести себя как обычный сундук; исправлена частота появления зелий.',
      } },
    ],
  },
  {
    version: 'v0.8.1',
    title: { en: 'Water Effects, Trap & Shield Fixes', ru: 'Водные эффекты, исправления ловушек и щита' },
    changes: [
      { description: {
        en: 'In-place respawn on Easy and Medium difficulty — your hero is reborn at the floor\'s stairs with 50% HP, debuffs cleared and a 3-turn spawn-protection window. Max 3 resurrections per run; boss-floor deaths are final (no respawn on floors 5, 10, 15, ...).',
        ru: 'Возрождение на месте на лёгком и среднем уровне сложности — герой возрождается на лестнице этажа с 50% HP, снятыми негативными эффектами и защитой на 3 хода. Максимум 3 возрождения за забег; на этажах боссов возрождение недоступно (смерть там окончательна).',
      } },
      { description: {
        en: 'Easy keeps your full gear on respawn; Medium keeps just your equipped weapon and armor; Hard has no respawn and scatters everything. UI difficulty labels renamed: NORMAL → MEDIUM, HARD → NORMAL — only the labels moved, not the difficulty progression or mob-AI aggression tiers.',
        ru: 'На лёгком сохраняется всё снаряжение; на среднем — только экипированные оружие и броня; на сложном возрождения нет, всё рассыпается. Метки сложности переименованы: НОРМА → СРЕДНЕ, СЛОЖНО → НОРМА — изменились только названия, не прогрессия сложности или агрессия ИИ мобов.',
      } },
      { description: {
        en: 'Score penalties for respawns: each resurrection halves your score (3 respawns → 12.5%); witnessing a teammate\'s resurrection shaves 25% per use, floored at 10%.',
        ru: 'Штрафы к очкам за возрождения: каждое возрождение делит счёт пополам (3 возрождения → 12.5%); возрождение союзника, которое вы видели, снижает счёт на 25% за каждое, с порогом 10%.',
      } },
      { description: {
        en: 'Resurrect dialog and HUD badge show respawns remaining; the death screen reflects whether your gear was scattered where you fell.',
        ru: 'Диалог возрождения и значок в HUD показывают оставшиеся возрождения; экран смерти отображает, было ли рассыпано снаряжение на месте гибели.',
      } },
      { description: {
        en: 'Fixed React StrictMode double-connect leaving heroes stuck as AFK ghosts when a stale first socket\'s disconnect arrived after the second socket had already rebound for the same session.',
        ru: 'Исправлена ошибка React StrictMode double-connect, из-за которой герои застревали как AFK-призраки, когда отключение первого устаревшего сокета приходило после того, как второй уже переподключился для того же сеанса.',
      } },
      { description: {
        en: 'Trap visibility fix: Worn Dart, Poison Dart, Rockfall, Disintegration and Grim traps are now always visible (matching SPD\'s canBeHidden=false) instead of sometimes spawning hidden.',
        ru: 'Исправление видимости ловушек: Изношенный дротик, Отравленный дротик, Камнепад, Распад и Жуткая ловушки теперь всегда видны (соответствует canBeHidden=false из SPD) вместо того, чтобы иногда появляться скрытыми.',
      } },
      { description: {
        en: 'Removed the obsolete entrance-room passive heal; the well_fed buff now drives the 3x regen bonus on its own. Mob door-open sounds now broadcast explicitly, and other players\' HP bars are always visible (2px tall, repositioned above the sprite).',
        ru: 'Удалён устаревший пассивный хил в комнате входа; теперь бафф «сытость» (well_fed) сам даёт тройной реген. Звуки открытия дверей мобами теперь транслируются явно, а полоски HP других игроков всегда видны (2px, перемещены над спрайтом).',
      } },
      { description: {
        en: 'Water effects: footsteps on water tiles now spawn animated ripples (ported from SPD Ripple.java), gated by flying/levitation checks; Halls dungeon floors render animated steam drifting over water (ported from SPD HallsLevel.Stream).',
        ru: 'Водные эффекты: шаги по воде теперь порождают анимированные рябь (порт из SPD Ripple.java), с проверкой полёта/левитации; этажи Чертогов отрисовывают анимированный пар над водой (порт из SPD HallsLevel.Stream).',
      } },
      { description: {
        en: 'Trap search fix: the Search action now always reveals all searchable hidden traps in range, matching SPD. Tengu\'s arena dart traps are flagged unsearchable so they stay hidden until triggered.',
        ru: 'Исправление поиска ловушек: действие «Поиск» теперь всегда обнаруживает все доступные для поиска скрытые ловушки в радиусе, как в SPD. Ловушки дротиков Тэнгу на арене помечены как не подлежащие поиску и остаются скрытыми до срабатывания.',
      } },
      { description: {
        en: 'Explosive trap fix: triggering an Explosive Trap now plays the correct bomb-blast VFX and screen shake instead of fire particles. Traps now properly affect non-player entities (mobs falling into pits, pitfall trap gas scaling uses floor_id not player.floor_id).',
        ru: 'Исправление взрывной ловушки: срабатывание взрывной ловушки теперь воспроизводит правильные VFX взрыва и тряску экрана вместо частиц огня. Ловушки теперь корректно действуют на не-игровых сущностей (мобы, падающие в ямы; масштабирование газа ямы использует floor_id вместо player.floor_id).',
      } },
      { description: {
        en: 'Broken seal shield visualization: the Warrior\'s shield halo now renders correctly with proper layering and glow, matching SPD\'s shield-above-hp-bar layout.',
        ru: 'Визуализация щита сломанной печати: аура щита Воина теперь корректно отрисовывается с правильным наложением и свечением, соответствующим макету SPD (поверх полоски здоровья).',
      } },
    ],
  },
  {
    version: 'v0.6.2',
    title: { en: 'AFK Ghosts, Sewers & Alchemy Polish', ru: 'AFK-призраки, канализация и алхимия' },
    changes: [
      { description: {
        en: 'When your connection drops, your hero now becomes an invisible, un-targetable "(AFK)" ghost instead of freezing in place; if you don\'t reconnect in time it dies through the normal death path (loot drop, grave) instead of vanishing.',
        ru: 'При обрыве соединения герой теперь превращается в невидимого неуязвимого AFK-призрака вместо того, чтобы просто замирать на месте; если вы не переподключитесь вовремя, персонаж проходит обычный путь смерти (сброс лута, могила) вместо исчезновения.',
      } },
      { description: {
        en: 'Reconnecting or refreshing the page now resumes your existing hero — position, HP and gear intact — instead of spawning a new one.',
        ru: 'Переподключение или обновление страницы теперь возвращает вас в того же героя — с прежней позицией, HP и снаряжением — вместо создания нового.',
      } },
      { description: {
        en: 'Swarm splitting now conserves HP across clones and spawns them next to the Swarm itself, matching the original game instead of appearing behind or beside the player.',
        ru: 'Деление Роя (Swarm) теперь сохраняет суммарное HP между клонами и создаёт их рядом с самим Роем, как в оригинале, а не позади или сбоку от игрока.',
      } },
      { description: {
        en: 'Mirror Image clones (Scroll of Mirror Image, Multiplicity glyph, Cursed Wand of Summon Monsters) now fight using the hero\'s actual weapon and ring stats instead of flat approximations.',
        ru: 'Клоны Зеркального образа (свиток Зеркального образа, руна Умножения, проклятый жезл Призыва монстров) теперь сражаются с характеристиками настоящего оружия и колец героя, а не с приблизительными значениями.',
      } },
      { description: {
        en: 'Sewers: six previously-empty standard rooms (Minefield, Plants, Aquarium, Fissure, Grassy Grave, Study) now have their real terrain, loot and mobs; Sentry, Magic Well and Sacrifice Fire special rooms are functional again.',
        ru: 'Канализация: шесть ранее пустых обычных комнат (Минное поле, Растения, Аквариум, Разлом, Мрачная могила, Кабинет) теперь получили настоящий рельеф, лут и мобов; особые комнаты Часового, Волшебного колодца и Огня жертвоприношения снова работают.',
      } },
      { description: {
        en: 'New in-game Alchemy Guide available from the alchemy pot\'s Guide button; ghost reward window and loot indicator visuals reworked to match the original.',
        ru: 'Новый алхимический справочник доступен по кнопке «Guide» у алхимического котла; переработаны окно награды от призрака и индикатор лута.',
      } },
      { description: {
        en: 'Alchemy pot workspace restyled to match the original look (red ingredient slots, correct hint text, matching button colors); tombs and chests now show distinct names and sounds.',
        ru: 'Мастерская алхимии переоформлена под оригинальный вид (красные слоты ингредиентов, правильный текст подсказки, соответствующие цвета кнопок); гробницы и сундуки теперь показывают отдельные названия и звуки.',
      } },
    ],
  },
  {
    version: 'v0.6.1',
    title: { en: 'Combat Feedback & AI Fixes', ru: 'Улучшения боя и ИИ' },
    changes: [
      { description: {
        en: 'Hit reactions now use SPD\'s two-tier warning sound — a sharper critical alert layers on top of the low-health warning, based on how much damage just landed and how little HP remains.',
        ru: 'Реакция на попадания теперь использует двухуровневый сигнал SPD — более резкий критический сигнал звучит поверх обычного предупреждения о низком здоровье, в зависимости от нанесённого урона и оставшегося HP.',
      } },
      { description: {
        en: 'Fixed boss mobs (like Goo) sometimes getting stuck at their spawn tile when their arena overlapped the level\'s entrance or secret room.',
        ru: 'Исправлена ошибка, из-за которой боссы (например, Гуи) иногда застревали на месте появления, если их арена пересекалась с комнатой входа или секретной комнатой уровня.',
      } },
      { description: {
        en: 'Mobs now track whether they can actually see their target and chase more reliably through doors, instead of losing the trail the instant line of sight briefly breaks.',
        ru: 'Мобы теперь отслеживают, действительно ли они видят цель, и надёжнее преследуют её через двери, вместо того чтобы сразу терять след при кратковременной потере видимости.',
      } },
    ],
  },
  {
    version: 'v0.6.0',
    title: { en: 'Wandmaker & Library Rooms', ru: 'Мастер жезлов и библиотеки' },
    changes: [
      { description: {
        en: 'Wandmaker quest on Prison depths 6-9: Corpse Dust, Rotberry and Ceremonial Candle variants, each granting a wand reward.',
        ru: 'Квест Мастера жезлов на этажах 6-9 Тюрьмы: варианты Трупной пыли, Гнилевицы и Церемониальной свечи, каждый даёт в награду жезл.',
      } },
      { description: {
        en: 'Library special rooms: bookshelf wall stitching plus crystal doors and barricades rendered correctly in the wall atlas.',
        ru: 'Особые комнаты библиотеки: стыковка стен с книжными шкафами, а также кристальные двери и баррикады, теперь корректно отрисовываются в атласе стен.',
      } },
      { description: {
        en: 'Fixed a wall-atlas regression that broke ordinary rooms\' straight side walls with black gaps.',
        ru: 'Исправлена регрессия атласа стен, из-за которой прямые боковые стены обычных комнат отображались с чёрными провалами.',
      } },
      { description: {
        en: 'Server stability: isolated per-game exceptions in the global game loop and fixed a connection-list mutation race, so one game crashing no longer freezes broadcasting for every other game on the server.',
        ru: 'Стабильность сервера: исключения теперь изолируются по каждой игре в общем игровом цикле, исправлена гонка при изменении списка соединений — краш одной игры больше не замораживает рассылку состояния для всех остальных игр на сервере.',
      } },
      { description: {
        en: 'Wooden special-room floors (Library, Storage, Treasury) now play the original SPD \'sturdy\' step sound instead of the generic footstep.',
        ru: 'Деревянный пол особых комнат (Библиотека, Склад, Сокровищница) теперь воспроизводит оригинальный звук шагов SPD «sturdy» вместо обычного звука шагов.',
      } },
    ],
  },
  {
    version: 'v0.5.0',
    title: { en: 'Alchemy Scene', ru: 'Сцена алхимии' },
    changes: [
      { description: {
        en: 'New full-screen Alchemy scene: walk into the alchemy pot to open a redesigned brewing workspace with a water background and live bubble particles.',
        ru: 'Новая полноэкранная сцена алхимии: подойдите к котлу, чтобы открыть переработанную мастерскую с водным фоном и живыми пузырьками.',
      } },
      { description: {
        en: 'Ingredient picker now follows Shattered Pixel Dungeon recipe rules — only valid reagents (identified/uncursed wands, uncursed trinkets, potions, scrolls, seeds and more) can be selected.',
        ru: 'Выбор ингредиентов теперь следует правилам рецептов Shattered Pixel Dungeon — можно выбрать только подходящие реагенты (опознанные/непроклятые жезлы, непроклятые безделушки, зелья, свитки, семена и другое).',
      } },
      { description: {
        en: 'Alchemy pots on the map now bubble with animated particles.',
        ru: 'Котлы алхимии на карте теперь пузырятся анимированными частицами.',
      } },
      { description: {
        en: 'Rendering fix: wall tops bordering visible floor no longer render as black gaps.',
        ru: 'Исправление отрисовки: верх стен на границе видимого пола больше не отображается чёрными провалами.',
      } },
    ],
  },
  {
    version: 'v0.4.11',
    title: { en: 'Onboarding Tutorial & HUD Polish', ru: 'Обучающий туториал и полировка HUD' },
    changes: [
      { description: {
        en: 'Interactive attack demo canvas (bump + ranged) in the onboarding tutorial.',
        ru: 'Интерактивная демонстрация атак (ближний бой + дальний) в обучающем туториале.',
      } },
      { description: {
        en: 'Flying item pickup animation: items fly to the inventory button on pickup.',
        ru: 'Анимация полёта предмета при подборе: предметы летят к кнопке инвентаря.',
      } },
      { description: {
        en: 'Toolbar quickslots: waterskin volume (N/20), dynamic font sizing for counts, hover tooltips with keybind hints.',
        ru: 'Быстрые слоты панели инструментов: объём фляги (N/20), динамический размер шрифта для количеств, всплывающие подсказки с привязками клавиш.',
      } },
      { description: {
        en: 'Inventory pane: bag capacity captions (N/M) on tabs, zoom compensation, just-identified glow, equipped badge (E).',
        ru: 'Панель инвентаря: ёмкость сумки (N/M) на вкладках, компенсация зума, свечение только что найденного, значок экипировки (E).',
      } },
      { description: {
        en: 'Enhanced (blue) / warning (orange) upgrade level tints in inventory, pure level-color module.',
        ru: 'Улучшенные (синие) / предупреждающие (оранжевые) оттенки уровней в инвентаре, чистый модуль цвета уровня.',
      } },
      { description: {
        en: 'Item inspect via long-press/right-click in selector mode, inline selector prompt, Tab/[ ] bag cycling.',
        ru: 'Осмотр предмета долгим нажатием/правым кликом в режиме селектора, инлайн-промпт селектора, переключение сумок Tab/[ ].',
      } },
      { description: {
        en: 'Desktop hover tooltips with keybind hints for quickslot items.',
        ru: 'Всплывающие подсказки на десктопе с привязками клавиш для предметов в быстрых слотах.',
      } },
    ],
  },
  {
    version: 'v0.4.6',
    title: { en: 'Huntress & Rings Update', ru: 'Обновление Охотницы и колец' },
    changes: [
      { description: {
        en: 'New playable class: Huntress with SPD-accurate Spirit Bow (infinite ammo, level-scaling, auto-quickslot).',
        ru: 'Новый класс: Охотница с Луком Духа (SPD-точная механика: бесконечные стрелы, масштабирование с уровнем, авто-слот).',
      } },
      { description: {
        en: 'All 12 SPD rings: Force, Elements, Wealth — full ring generation, identification and equipment.',
        ru: 'Все 12 колец SPD: Силы, Стихий, Богатства — полная генерация, опознание и экипировка.',
      } },
      { description: {
        en: 'SPD-accurate scroll behaviors: Teleportation prefers secret rooms, Identify/Remove Curse/Transmutation always opens dialog.',
        ru: 'SPD-точное поведение свитков: телепортация в секретные комнаты, опознание/снятие проклятия всегда с диалогом.',
      } },
      { description: {
        en: 'Invisibility potion with gradual fade (0.4 alpha over 0.4s matching SPD) and mob last-known-position AI.',
        ru: 'Зелье невидимости с постепенным затуханием (0.4 альфа за 0.4с) и AI мобов с запоминанием последней позиции.',
      } },
      { description: {
        en: 'Magic missile glow trail, auto-target double-click, LOS-free wand zaps via ballistica.',
        ru: 'Магический снаряд с эффектом свечения, авто-цель по двойному клику, заклинания без LOS через ballistica.',
      } },
      { description: {
        en: 'Wand of Lightning VFX/SFX, electricity blob lifetime cap, Goo death drops.',
        ru: 'Визуальные/звуковые эффекты молнии, ограничение времени жизни электричества, выпадение предметов из Гу.',
      } },
      { description: {
        en: 'Per-weapon melee hit sounds, boss health bars, bag tabs on equip row (SPD layout).',
        ru: 'Звуки ударов для каждого оружия, полоса здоровья боссов, вкладки сумок в ряду экипировки (SPD).',
      } },
      { description: {
        en: 'Bug fixes: player vanishing, sub-bag scatter on death, surprise attack crash, hunger starvation disabled, SPD-faithful Sewers lore.',
        ru: 'Исправления: исчезновение игрока, разброс сумок при смерти, краш внезапных атак, отключен урон от голода, лор канализации.',
      } },
    ],
  },
  {
    version: 'v0.4.5',
    title: { en: 'Side Door Sync', ru: 'Синхронизация дверей' },
    changes: [
      { description: {
        en: 'Fixed side door open/closed state not syncing between clients.',
        ru: 'Исправлена синхронизация состояния боковых дверей между клиентами.',
      } },
    ],
  },
  {
    version: 'v0.4.4',
    title: { en: 'Scroll & Surprise Fixes', ru: 'Исправление свитков и внезапных атак' },
    changes: [
      { description: {
        en: 'Scroll of Recharging changed from instant full refill to regen-speed multiplier (matches SPD).',
        ru: 'Свиток перезарядки: мгновенное восстановление заменено множителем скорости регенерации (соответствие SPD).',
      } },
      { description: {
        en: 'Scroll of Teleportation prefers SpecialRoom interiors; secret doors auto-discovered at destination.',
        ru: 'Свиток телепортации предпочитает комнаты SpecialRoom; секретные двери автоматически обнаруживаются у точки назначения.',
      } },
      { description: {
        en: 'Scroll of Identify/Remove Curse/Transmutation: dialog always opens; unidentified scrolls consumed on read (SPD match).',
        ru: 'Свитки опознания/снятия проклятия/трансмутации: диалог открывается всегда; неопознанные свитки расходуются при чтении (SPD).',
      } },
      { description: {
        en: 'Scroll of Rage no longer amoks allies (matches SPD).',
        ru: 'Свиток ярости больше не действует на союзников (соответствие SPD).',
      } },
      { description: {
        en: 'Scroll of Magic Mapping only marks discoverable tiles; secret discovery restricted to FOV.',
        ru: 'Свиток магической карты отмечает только проходимые клетки; секреты обнаруживаются только в поле зрения.',
      } },
      { description: {
        en: 'Blindness and magic immunity block scroll reading (SPD match).',
        ru: 'Слепота и иммунитет к магии блокируют чтение свитков (SPD).',
      } },
      { description: {
        en: 'Scroll generation uses SPD probability weights for balanced loot distribution.',
        ru: 'Генерация свитков использует вероятности SPD для сбалансированного распределения добычи.',
      } },
      { description: {
        en: 'Degrade buff removed on Upgrade/Remove Curse scroll use (SPD match).',
        ru: 'Дебафф понижения снимается при использовании свитка улучшения/снятия проклятия (SPD).',
      } },
      { description: {
        en: 'Fixed ReferenceError crash on surprise attacks (snake vs mirror image).',
        ru: 'Исправлена ошибка ReferenceError при внезапных атаках (змея против зеркального образа).',
      } },
      { description: {
        en: 'Admin auto-identifies picked up potions/scrolls for easier testing.',
        ru: 'Администратор автоматически опознаёт подобранные зелья и свитки для упрощения тестирования.',
      } },
    ],
  },
  {
    version: 'v0.4.2',
    title: { en: 'Tengu & Items Bugfix', ru: 'Исправление Тэнгу и предметов' },
    changes: [
      { description: {
        en: 'Added Tengu\'s Mask and King\'s Crown items with inventory serialization and sprite fixes.',
        ru: 'Добавлены Маска Тэнгу и Корона Короля с сериализацией инвентаря и исправлением спрайтов.',
      } },
      { description: {
        en: 'Fixed Tengu arena layout level exiting and boss tracking mechanics.',
        ru: 'Исправлен выход с арены Тэнгу и отслеживание статуса босса.',
      } },
      { description: {
        en: 'Resolved issues with integer conversion of entity health during state updates.',
        ru: 'Решено преобразование здоровья сущностей в целые числа при обновлении состояния.',
      } },
    ],
  },
  {
    version: 'v0.4.1',
    title: { en: 'Scroll VFX/SFX Polish', ru: 'Улучшение эффектов свитков' },
    changes: [
      { description: {
        en: 'Add per-scroll particle emitters mirroring SPD\'s Speck types.',
        ru: 'Добавлены эффекты частиц для каждого типа свитков, аналогично оригинальной SPD.',
      } },
      { description: {
        en: 'Rewrite StatusPane to large-layout (PC) with health/shield/EXP bars.',
        ru: 'Переписан интерфейс панели статуса под большой макет (ПК) с полосками здоровья/щита/опыта.',
      } },
    ],
  },
  {
    version: 'v0.4.0',
    title: { en: 'Warrior Update', ru: 'Обновление воина' },
    changes: [
      { description: {
        en: 'Full Warrior talent tree: T1-T3 talents, Berserk and Combo mechanics, Gladiator finisher moves.',
        ru: 'Полное дерево талантов воина: таланты T1-T3, механики берсерка и комбо, финишеры гладиатора.',
      } },
      { description: {
        en: 'New armor abilities including Endure.',
        ru: 'Новые броневые способности, включая Стойкость.',
      } },
      { description: {
        en: 'Expanded melee weapon roster and weapon enchantments/curses.',
        ru: 'Расширенный арсенал оружия ближнего боя и зачарования/проклятия оружия.',
      } },
      { description: {
        en: 'Admin item browser (press U) to spawn any item for testing.',
        ru: 'Админский обзор предметов (U) для спавна любых предметов в тестовых целях.',
      } },
      { description: {
        en: 'Combat rework: damage multipliers/bonuses, guaranteed hits, and enchant-driven procs.',
        ru: 'Переработка боя: множители урона, гарантированные попадания и срабатывания зачарований.',
      } },
    ],
  },
  {
    version: 'v0.3.1',
    title: { en: 'Shops & Economy Update', ru: 'Обновление магазинов и экономики' },
    changes: [
      { description: {
        en: 'Shop rooms: buy and sell items with gold.',
        ru: 'Комнаты магазинов: покупка и продажа предметов за золото.',
      } },
      { description: {
        en: 'Gold pickup and item value/identification data for the full item set.',
        ru: 'Подбор золота и данные о стоимости/опознании для всех предметов.',
      } },
      { description: {
        en: 'Imp quest and waterskin item.',
        ru: 'Квест импа и фляга с водой.',
      } },
      { description: {
        en: 'Quickslot bag UI improvements and wall-fog rendering fixes.',
        ru: 'Улучшения интерфейса быстрых слотов и исправления рендеринга тумана стен.',
      } },
      { description: {
        en: 'Vision/shadowcasting parity fixes.',
        ru: 'Исправления обзора и расчёта теней.',
      } },
    ],
  },
  {
    version: 'v0.3.0',
    title: { en: 'Bosses & Dungeon Regions Update', ru: 'Обновление боссов и регионов' },
    changes: [
      { description: {
        en: 'Full SPD-faithful level generation for all 5 dungeon regions: Sewers, Prison, Caves, City and Halls.',
        ru: 'Генерация уровней для всех 5 регионов: Канализация, Тюрьма, Пещеры, Город и Чертоги.',
      } },
      { description: {
        en: 'New floor 5/10/15/20/25 boss fights: Goo, Tengu, DM-300, Dwarf King and Yog-Dzewa, each with their own AI and arena.',
        ru: 'Битвы с боссами на этажах 5/10/15/20/25: Гу, Тэнгу, DM-300, Король гномов и Йог-Дзева, каждый со своим ИИ и ареной.',
      } },
      { description: {
        en: '24 new mob types added across the new regions.',
        ru: '24 новых типа мобов в новых регионах.',
      } },
      { description: {
        en: 'Hunger system: characters start starving at 450 and food items reduce hunger.',
        ru: 'Система голода: персонаж начинает голодать на 450, еда снижает голод.',
      } },
      { description: {
        en: 'All 12 base potions, 12 base scrolls and food items added.',
        ru: 'Все 12 базовых зелий, 12 свитков и предметов еды.',
      } },
      { description: {
        en: 'New combat sound effects for blasts, lightning, rays, scrolls and locks.',
        ru: 'Новые звуковые эффекты для взрывов, молний, лучей, свитков и замков.',
      } },
    ],
  },
  {
    version: 'v0.2.0',
    title: { en: 'Combat & Controls Update', ru: 'Обновление боя и управления' },
    changes: [
      { description: {
        en: 'SPD-style critical hits: surprise attacks, damage floors, Fury and weapon enchants.',
        ru: 'Критические удары в стиле SPD: внезапные атаки, минимальный урон, Ярость и чары оружия.',
      } },
      { description: {
        en: 'Misses now show visual and audio feedback.',
        ru: 'Промахи теперь показывают визуальную и звуковую обратную связь.',
      } },
      { description: {
        en: '8-directional movement with diagonal walking; smoother keyboard input.',
        ru: 'Движение по 8 направлениям с диагональной ходьбой; улучшенный ввод с клавиатуры.',
      } },
      { description: {
        en: 'Line-of-sight rewritten with the original recursive shadowcasting.',
        ru: 'Линия обзора переписана с использованием оригинального рекурсивного расчёта теней.',
      } },
      { description: {
        en: 'Visible traps with proper terrain rendering.',
        ru: 'Видимые ловушки с правильным рендерингом местности.',
      } },
      { description: {
        en: 'Mobile toolbar: quick-bag, radial menu and slot swapping; fixed mobile travel and ranged attacks.',
        ru: 'Мобильная панель: быстрая сумка, радиальное меню и смена слотов; исправлены мобильные перемещения и дальние атаки.',
      } },
      { description: {
        en: 'Custom cursor across landing and hero screens; camera keeps the player centered at high zoom.',
        ru: 'Пользовательский курсор на экранах меню и выбора героя; камера держит игрока в центре при большом зуме.',
      } },
      { description: {
        en: 'Ported the original inventory and UI elements; fixed item inspect, throwing and labels.',
        ru: 'Перенесены оригинальные элементы инвентаря и интерфейса; исправлены осмотр предметов, метание и подписи.',
      } },
      { description: {
        en: 'Reworked armor and damage flow; fixed mob attack timing and global passive healing.',
        ru: 'Переработан расчёт брони и урона; исправлены тайминги атак мобов и глобальное пассивное лечение.',
      } },
      { description: {
        en: 'Entrance room is now a healing room.',
        ru: 'Входная комната теперь является комнатой лечения.',
      } },
    ],
  },
  {
    version: 'v0.1.0',
    title: { en: 'Online Pixel Dungeon — Title Update', ru: 'Online Pixel Dungeon — Титульное обновление' },
    changes: [
      { description: {
        en: 'New animated main menu: scrolling parallax background, banner with pulsing glow, and two flickering torches — ported from the original Shattered Pixel Dungeon title screen.',
        ru: 'Новое анимированное главное меню: параллакс-фон, светящийся баннер и два мерцающих факела — перенесено из оригинального Shattered Pixel Dungeon.',
      } },
      { description: {
        en: 'Added Settings (audio + display), Changes, Guide, About, Rankings and News screens.',
        ru: 'Добавлены экраны настроек (звук + отображение), изменений, руководства, об игре, рейтинга и новостей.',
      } },
      { description: {
        en: 'Audio now has independent music and SFX volume controls plus a master mute.',
        ru: 'Независимая регулировка громкости музыки и звуковых эффектов, а также общее отключение звука.',
      } },
      { description: {
        en: 'Display option to toggle background animations.',
        ru: 'Опция отключения фоновых анимаций в настройках отображения.',
      } },
    ],
  },
  {
    version: 'v0.0.x',
    title: { en: 'Early Online Prototype', ru: 'Ранний онлайн-прототип' },
    changes: [
      { description: {
        en: 'Real-time multiplayer dungeon over WebSocket.',
        ru: 'Мультиплеерное подземелье в реальном времени через WebSocket.',
      } },
      { description: {
        en: 'Four playable classes: Warrior, Mage, Rogue, Archer.',
        ru: 'Четыре играбельных класса: Воин, Маг, Плуг, Лучница.',
      } },
      { description: {
        en: 'Canvas-rendered dungeon with mobs, items, inventory and combat.',
        ru: 'Подземелье с мобами, предметами, инвентарём и боем, отрисованное на канвасе.',
      } },
      { description: {
        en: 'Depth-based music and sound effects.',
        ru: 'Музыка и звуковые эффекты, зависящие от глубины.',
      } },
    ],
  },
];

export default CHANGELOG;
