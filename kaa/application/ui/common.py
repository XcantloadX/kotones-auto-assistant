from typing import List, Dict, Tuple, Callable, Any, Literal, Optional
from dataclasses import dataclass, field
import gradio as gr
from kaa.config.schema import BaseConfig

# Type hints
GradioInput = gr.Textbox | gr.Number | gr.Checkbox | gr.Dropdown | gr.Radio | gr.Slider | gr.State
ConfigKey = Literal[
    # backend
    'backend_type', 'adb_ip', 'adb_port',
    'screenshot_method', 'keep_screenshots',
    'check_emulator', 'emulator_path',
    'adb_emulator_name', 'emulator_args',
    '_mumu_index', '_mumu12v5_index', '_leidian_index',
    'mumu_background_mode_v4', 'mumu_background_mode_v5', 'target_screenshot_interval',

    # purchase
    'purchase_enabled',
    'money_enabled', 'ap_enabled',
    'ap_items', 'money_items', 'money_refresh',
    
    # assignment
    'assignment_enabled',
    'mini_live_reassign', 'mini_live_duration',
    'online_live_reassign', 'online_live_duration',
    'contest_enabled',
    'select_which_contestant', 'when_no_set',
    
    # produce
    'produce_enabled', 'selected_solution_id', 'produce_count', 'produce_timeout_cd', 'interrupt_timeout', 'enable_fever_month',
    'mission_reward_enabled',
    
    # club reward
    'club_reward_enabled',
    'selected_note',
    
    # upgrade support card
    'upgrade_support_card_enabled',
    
    # capsule toys
    'capsule_toys_enabled', 'friend_capsule_toys_count',
    'sense_capsule_toys_count', 'logic_capsule_toys_count',
    'anomaly_capsule_toys_count',
    
    # start game
    'start_game_enabled', 'start_through_kuyo',
    'game_package_name', 'kuyo_package_name',
    'disable_gakumas_localify', 'dmm_game_path', 'dmm_bypass',

    # end game
    'exit_kaa', 'kill_game', 'kill_dmm',
    'kill_emulator', 'shutdown', 'hibernate',
    'restore_gakumas_localify',
    
    'activity_funds',
    'presents',
    'mission_reward',
    'activity_funds_enabled',
    'presents_enabled',
    'trace_recommend_card_detection',
    
    # misc
    'check_update', 'auto_install_update', 'expose_to_lan', 'update_channel', 'log_level',

    # idle
    'idle_enabled', 'idle_seconds', 'idle_minimize_on_pause',

    '_selected_backend_index'
    
]
ConfigSetFunction = Callable[[BaseConfig, Dict[ConfigKey, Any]], None]
ConfigBuilderReturnValue = Tuple[ConfigSetFunction, Dict[ConfigKey, GradioInput]]


@dataclass
class GradioComponents:
    """Dataclass to hold all Gradio UI components that need to be accessed across methods."""
    
    # Main tabs
    tabs: Optional[gr.Tabs] = None
    
    # Status tab components
    run_btn: Optional[gr.Button] = None
    pause_btn: Optional[gr.Button] = None
    end_action_dropdown: Optional[gr.Dropdown] = None
    quick_checkboxes: List[gr.Checkbox] = field(default_factory=list)
    task_runtime_text: Optional[gr.Textbox] = None
    task_status_df: Optional[gr.Dataframe] = None
    
    # Update tab components
    update_info_md: Optional[gr.Markdown] = None
    update_status_text: Optional[gr.Markdown] = None
    update_version_dropdown: Optional[gr.Dropdown] = None
    update_install_btn: Optional[gr.Button] = None
    
    # Produce tab components
    produce_tab_solution_dropdown: Optional[gr.Dropdown] = None
    produce_solution_settings_group: Optional[gr.Group] = None
    produce_solution_name: Optional[gr.Textbox] = None
    produce_solution_description: Optional[gr.Textbox] = None
    produce_mode: Optional[gr.Dropdown] = None
    produce_idols: Optional[gr.Dropdown] = None
    produce_auto_set_memory: Optional[gr.Checkbox] = None
    produce_memory_sets_group: Optional[gr.Group] = None
    produce_memory_sets: Optional[gr.Dropdown] = None
    produce_auto_set_support: Optional[gr.Checkbox] = None
    produce_support_card_sets_group: Optional[gr.Group] = None
    produce_support_card_sets: Optional[gr.Dropdown] = None
    produce_use_pt_boost: Optional[gr.Checkbox] = None
    produce_use_note_boost: Optional[gr.Checkbox] = None
    produce_follow_producer: Optional[gr.Checkbox] = None
    produce_self_study_lesson: Optional[gr.Dropdown] = None
    produce_prefer_lesson_ap: Optional[gr.Checkbox] = None
    produce_actions_order: Optional[gr.Dropdown] = None
    produce_recommend_card_detection_mode: Optional[gr.Dropdown] = None
    produce_use_ap_drink: Optional[gr.Checkbox] = None
    produce_skip_commu: Optional[gr.Checkbox] = None
    produce_all_detail_components: List[Any] = field(default_factory=list)
    
    # Settings tab components
    settings_solution_dropdown: Optional[gr.Dropdown] = None
    save_settings_btn: Optional[gr.Button] = None
