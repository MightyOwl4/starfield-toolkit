# Contract: Tool Module Interface

Every tool module (built-in or future external) MUST implement this interface
to be bootstrapped by the application shell.

## Module Metadata (class-level)

| Property    | Type | Description                                    |
| ----------- | ---- | ---------------------------------------------- |
| name        | str  | Short name displayed on the tab label          |
| description | str  | One-line description for tooltips/about screen |

## Initialization

The bootstrapper calls `initialize(context)` passing a `ModuleContext`
containing:

| Field              | Type              | Description                           |
| ------------------ | ----------------- | ------------------------------------- |
| game_installation  | GameInstallation  | Detected game paths model             |
| status_bar         | StatusBarAPI      | API to set/clear task messages        |
| content_frame      | Frame             | The UI frame allocated for this tab   |

## StatusBarAPI

| Method                    | Description                              |
| ------------------------- | ---------------------------------------- |
| `set_task(message: str)`  | Display a task message in segment 2      |
| `clear_task()`            | Clear the task message (shows "Ready")   |

## Lifecycle

1. Shell discovers module (from registry list)
2. Shell reads `name` and `description` (before game path is known)
3. Shell creates tab with `name` as label
4. Once game path is verified, shell calls `initialize(context)`
5. Module renders its UI into `content_frame`

If game path is NOT verified, the shell renders a placeholder warning in
the tab's content area. The module's `initialize()` is NOT called until a
valid path is provided.

## Registration

Built-in modules are registered in a single list (e.g.,
`src/tools/__init__.py` or a `MODULES` list in the app's config). Adding
a new module requires:
1. Create the module file in `src/tools/`
2. Add one import/entry to the registry list

No other files need modification.
