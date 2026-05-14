"""Tool schemas for mq9 Hermes plugin."""

MQ9_REGISTER_SELF = {
    "name": "mq9_register_self",
    "description": (
        "Register this Hermes instance into mq9 agent registry as a protocol-agnostic endpoint. "
        "Creates mailbox if needed and stores AgentCard for discovery."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "agent_name": {
                "type": "string",
                "description": "Override agent name for this registration.",
            },
            "mailbox": {
                "type": "string",
                "description": "Override mailbox name/address for this registration.",
            },
            "description": {
                "type": "string",
                "description": "Override agent description in AgentCard.",
            },
            "tags": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Optional tags for discovery filtering.",
            },
            "protocols": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Declared upper-layer protocols (e.g. ['a2a']).",
            },
            "metadata": {
                "type": "object",
                "description": "Extra metadata merged into AgentCard.metadata.",
            },
            "agent_card": {
                "type": "object",
                "description": (
                    "Optional complete AgentCard object to register directly. "
                    "When provided, plugin only ensures name/mailbox/protocol metadata."
                ),
            },
            "ensure_runtime": {
                "type": "boolean",
                "description": "Start passive runtime before registration (default true).",
            },
        },
    },
}

MQ9_UNREGISTER_SELF = {
    "name": "mq9_unregister_self",
    "description": (
        "Unregister this Hermes instance from mq9 agent registry. "
        "By default unregisters all names tracked by runtime."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "agent_name": {
                "type": "string",
                "description": "Optional explicit agent name to unregister.",
            },
        },
    },
}

MQ9_DISCOVER = {
    "name": "mq9_discover",
    "description": (
        "Discover remote agents from mq9 registry by natural-language query, "
        "and normalize mailbox info for direct mq9 calls. "
        "Optional protocol filter supports A2A or other upper-layer protocols."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Natural language query, e.g. 'Python HTTP server'.",
            },
            "limit": {
                "type": "integer",
                "description": "Max number of agents to return (default 10).",
                "minimum": 1,
                "maximum": 100,
            },
            "prefer_name": {
                "type": "string",
                "description": "If set, rank exact-name match first.",
            },
            "protocol": {
                "type": "string",
                "description": "Optional protocol filter, e.g. 'a2a'.",
            },
            "require_protocol": {
                "type": "boolean",
                "description": (
                    "If true, only return agents that explicitly declare this protocol. "
                    "If false, undeclared cards are allowed."
                ),
            },
        },
    },
}

MQ9_CALL = {
    "name": "mq9_call",
    "description": (
        "Send a task to a remote agent mailbox and wait for callback reply. "
        "If target_mailbox is missing, plugin will try mq9_discover(query). "
        "This is transport-level call; message payload stays protocol-opaque."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "target_mailbox": {
                "type": "string",
                "description": "Target mailbox address, e.g. hermes.b.python.inbox",
            },
            "query": {
                "type": "string",
                "description": "Discover query used when target_mailbox is not provided.",
            },
            "prefer_name": {
                "type": "string",
                "description": "Preferred agent name when discover is used.",
            },
            "message": {
                "description": "Task payload to send. Object is recommended; string is allowed.",
            },
            "protocol": {
                "type": "string",
                "description": "Upper-layer protocol name (default from config, typically 'a2a').",
            },
            "require_protocol": {
                "type": "boolean",
                "description": (
                    "When discover is used, require the discovered agent to explicitly "
                    "declare the selected protocol."
                ),
            },
            "content_type": {
                "type": "string",
                "description": "Optional payload content-type metadata.",
            },
            "context": {
                "type": "object",
                "description": "Optional out-of-band context metadata.",
            },
            "from_agent": {
                "type": "string",
                "description": "Caller agent name in envelope.",
            },
            "timeout_s": {
                "type": "number",
                "description": "Timeout seconds for reply wait (default 25).",
                "minimum": 1,
                "maximum": 300,
            },
        },
        "required": ["message"],
    },
}

MQ9_STATUS = {
    "name": "mq9_status",
    "description": "Return mq9 plugin runtime status and effective config.",
    "parameters": {
        "type": "object",
        "properties": {},
    },
}


A2A_REGISTER_SELF = {
    "name": "a2a_register_self",
    "description": (
        "Register this Hermes instance as an A2A-capable endpoint over mq9 transport. "
        "Equivalent to mq9_register_self with protocol='a2a'."
    ),
    "parameters": MQ9_REGISTER_SELF["parameters"],
}


A2A_DISCOVER = {
    "name": "a2a_discover",
    "description": (
        "Discover A2A-capable agents over mq9 transport. "
        "Equivalent to mq9_discover with protocol='a2a'."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Natural language query, e.g. 'Python HTTP server'.",
            },
            "limit": {
                "type": "integer",
                "description": "Max number of agents to return (default 10).",
                "minimum": 1,
                "maximum": 100,
            },
            "prefer_name": {
                "type": "string",
                "description": "If set, rank exact-name match first.",
            },
            "require_protocol": {
                "type": "boolean",
                "description": "Require explicit 'a2a' protocol declaration (default true).",
            },
        },
    },
}


A2A_CALL = {
    "name": "a2a_call",
    "description": (
        "Call a remote A2A-capable agent over mq9 transport. "
        "Equivalent to mq9_call with protocol='a2a'."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "target_mailbox": {
                "type": "string",
                "description": "Target mailbox address, e.g. hermes.b.python.inbox",
            },
            "query": {
                "type": "string",
                "description": "Discover query used when target_mailbox is not provided.",
            },
            "prefer_name": {
                "type": "string",
                "description": "Preferred agent name when discover is used.",
            },
            "message": {
                "description": "A2A message payload object.",
            },
            "require_protocol": {
                "type": "boolean",
                "description": "Require explicit 'a2a' protocol declaration (default true).",
            },
            "content_type": {
                "type": "string",
                "description": "Optional content-type metadata (default application/json).",
            },
            "context": {
                "type": "object",
                "description": "Optional context metadata.",
            },
            "from_agent": {
                "type": "string",
                "description": "Caller agent name in envelope.",
            },
            "timeout_s": {
                "type": "number",
                "description": "Timeout seconds for reply wait (default 25).",
                "minimum": 1,
                "maximum": 300,
            },
        },
        "required": ["message"],
    },
}
