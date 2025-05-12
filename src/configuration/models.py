from enum import Enum
from typing import NamedTuple


class ModelCost(NamedTuple):
    input_cost_per_million_tokens: float
    output_cost_per_million_tokens: float


class Model(Enum):
    GPT_4_O = ("gpt-4o", ModelCost(input_cost_per_million_tokens=5.0, output_cost_per_million_tokens=15.0))
    GPT_4_1 = (
        "gpt-4.1",
        ModelCost(input_cost_per_million_tokens=10.0, output_cost_per_million_tokens=30.0),
    )  # Placeholder
    O3 = (
        "o3",
        ModelCost(input_cost_per_million_tokens=0.5, output_cost_per_million_tokens=1.5),
    )  # Placeholder for Opus
    O4_MINI = ("o4-mini", ModelCost(input_cost_per_million_tokens=0.15, output_cost_per_million_tokens=0.6))
    CLAUDE_SONNET_3_5 = (
        "claude-3-5-sonnet-latest",
        ModelCost(input_cost_per_million_tokens=3.0, output_cost_per_million_tokens=15.0),
    )
    CLAUDE_SONNET_3_7 = (
        "claude-3-7-sonnet-latest",
        ModelCost(input_cost_per_million_tokens=3.0, output_cost_per_million_tokens=15.0),
    )  # Placeholder - assuming same as 3.5 for now

    def __new__(cls, value, cost: ModelCost):
        obj = object.__new__(cls)
        obj._value_ = value
        obj.cost = cost
        return obj

    @property
    def model_name(self) -> str:
        return self.value

    def is_anthropic(self) -> bool:
        return self in [
            Model.CLAUDE_SONNET_3_5,
            Model.CLAUDE_SONNET_3_7,
        ]

    def get_costs(self) -> ModelCost:
        """Returns the input and output cost per million tokens for the model."""
        return self.cost
