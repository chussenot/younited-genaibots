from typing import List, Optional

from core.backend.internal_data_processing_base import InternalDataProcessingBase


class BackendInternalDataProcessingDispatcher(InternalDataProcessingBase):
    def __init__(self, global_manager):
        from core.global_manager import GlobalManager
        self.global_manager : GlobalManager = global_manager
        self.logger = self.global_manager.logger
        self.plugins : List[InternalDataProcessingBase] = []
        self.default_plugin_name = None
        self.default_plugin: Optional[InternalDataProcessingBase] = None

    def initialize(self, plugins: List[InternalDataProcessingBase] = None):
        if not plugins:
            self.logger.error("No plugins provided for BackendInternalDataProcessingDispatcher")
            return

        self.plugins = plugins
        self.default_plugin = plugins[0]
        self.default_plugin_name = self.default_plugin.plugin_name

    def get_plugin(self, plugin_name = None):
        if plugin_name is None:
            plugin_name = self.default_plugin_name

        for plugin in self.plugins:
            if plugin.plugin_name == plugin_name:
                return plugin

        self.logger.error(f"BackendInternalDataProcessingDispatcher: Plugin '{plugin_name}' not found, returning default plugin")
        return self.default_plugin

    @property
    def plugins(self) -> List[InternalDataProcessingBase]:
        return self._plugins

    @plugins.setter
    def plugins(self, value: List[InternalDataProcessingBase]):
        self._plugins = value

    @property
    def plugin_name(self, plugin_name = None):
        plugin : InternalDataProcessingBase = self.get_plugin(plugin_name)
        return plugin.plugin_name

    @plugin_name.setter
    def plugin_name(self, value):
        plugin : InternalDataProcessingBase = self.get_plugin()
        plugin.plugin_name = value

    @property
    def sessions(self, plugin_name = None):
        plugin : InternalDataProcessingBase = self.get_plugin(plugin_name)
        return plugin.sessions

    @property
    def messages(self, plugin_name = None):
        plugin : InternalDataProcessingBase = self.get_plugin(plugin_name)
        return plugin.messages

    @property
    def feedbacks(self, plugin_name = None):
        plugin : InternalDataProcessingBase = self.get_plugin(plugin_name)
        return plugin.feedbacks

    @property
    def concatenate(self, plugin_name = None):
        plugin : InternalDataProcessingBase = self.get_plugin(plugin_name)
        return plugin.concatenate

    @property
    def prompts(self, plugin_name = None):
        plugin : InternalDataProcessingBase = self.get_plugin(plugin_name)
        return plugin.prompts

    @property
    def costs(self, plugin_name = None):
        plugin : InternalDataProcessingBase = self.get_plugin(plugin_name)
        return plugin.costs

    @property
    def processing(self, plugin_name = None):
        plugin : InternalDataProcessingBase = self.get_plugin(plugin_name)
        return plugin.processing

    @property
    def abort(self, plugin_name = None):
        plugin : InternalDataProcessingBase = self.get_plugin(plugin_name)
        return plugin.abort

    @property
    def vectors(self, plugin_name = None):
        plugin : InternalDataProcessingBase = self.get_plugin(plugin_name)
        return plugin.vectors

    def append_data(self, container_name: str, data_identifier: str, data: str = None):
        plugin: InternalDataProcessingBase = self.get_plugin(container_name)
        plugin.append_data(container_name, data_identifier, data)

    async def read_data_content(self, data_container, data_file, plugin_name = None):
        plugin : InternalDataProcessingBase = self.get_plugin(plugin_name)
        return await plugin.read_data_content(data_container= data_container, data_file= data_file)

    async def write_data_content(self, data_container, data_file, data, plugin_name = None):
        plugin : InternalDataProcessingBase = self.get_plugin(plugin_name)
        await plugin.write_data_content(data_container= data_container, data_file= data_file, data= data)

    async def store_unmentioned_messages(self, channel_id, thread_id, message, plugin_name = None):
        plugin : InternalDataProcessingBase = self.get_plugin(plugin_name)
        await plugin.store_unmentioned_messages(channel_id= channel_id, thread_id= thread_id, message= message)

    async def retrieve_unmentioned_messages(self, channel_id, thread_id, plugin_name = None):
        plugin : InternalDataProcessingBase = self.get_plugin(plugin_name)
        return await plugin.retrieve_unmentioned_messages(channel_id= channel_id, thread_id= thread_id)

    async def update_pricing(self, container_name, datafile_name, pricing_data, plugin_name = None):
        plugin : InternalDataProcessingBase = self.get_plugin(plugin_name)
        return await plugin.update_pricing(container_name= container_name, datafile_name= datafile_name, pricing_data= pricing_data)

    async def update_prompt_system_message(self, channel_id, thread_id, message, plugin_name = None):
        plugin : InternalDataProcessingBase = self.get_plugin(plugin_name)
        await plugin.update_prompt_system_message(channel_id= channel_id, thread_id= thread_id, message= message)

    async def update_session(self, data_container, data_file, role, content, plugin_name = None):
        plugin : InternalDataProcessingBase = self.get_plugin(plugin_name)
        await plugin.update_session(data_container= data_container, data_file= data_file, role= role, content= content)

    async def remove_data_content(self, data_container, data_file, plugin_name = None):
        plugin : InternalDataProcessingBase = self.get_plugin(plugin_name)
        await plugin.remove_data_content(data_container= data_container, data_file= data_file)

    async def list_container_files(self, container_name, plugin_name = None):
        plugin : InternalDataProcessingBase = self.get_plugin(plugin_name)
        return await plugin.list_container_files(container_name= container_name)
