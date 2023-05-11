class MessagingService:
    def send_message(self, agent_id, topic, message):
        """
        Sends a message to a topic on behalf of the specified agent.
        """
        pass

    def receive_message(self, agent_id, topic):
        """
        Receives a message from a topic on behalf of the specified agent.
        """
        pass

    def subscribe_topic(self, agent_id, topic):
        """
        Subscribes the specified agent to a topic.
        """
        pass

    def unsubscribe_topic(self, agent_id, topic):
        """
        Unsubscribes the specified agent from a topic.
        """
        pass
