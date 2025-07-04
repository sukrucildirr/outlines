"""Integration with the `ollama` library."""

import json
from typing import TYPE_CHECKING, Any, Iterator, Optional

from pydantic import TypeAdapter

from outlines.models.base import Model, ModelTypeAdapter
from outlines.types import CFG, JsonSchema, Regex
from outlines.types.utils import (
    is_dataclass,
    is_genson_schema_builder,
    is_pydantic_model,
    is_typed_dict,
)

if TYPE_CHECKING:
    from ollama import Client as OllamaClient

__all__ = ["Ollama", "from_ollama"]


class OllamaTypeAdapter(ModelTypeAdapter):
    """Type adapter for the `Ollama` model."""

    def format_input(self, model_input: str) -> str:
        """Generate the prompt argument to pass to the model.

        Parameters
        ----------
        model_input
            The input provided by the user.

        Returns
        -------
        str
            The formatted input to be passed to the model.

        """
        if isinstance(model_input, str):
            return model_input
        raise TypeError(
            f"The input type {model_input} is not available. "
            "Ollama does not support batch inference."
        )

    def format_output_type(self, output_type: Optional[Any] = None) -> Optional[str]:
        """Format the output type to pass to the client.

        TODO: `int`, `float` and other Python types could be supported via
        JSON Schema.

        Parameters
        ----------
        output_type
            The output type provided by the user.

        Returns
        -------
        Optional[str]
            The formatted output type to be passed to the model.

        """
        if isinstance(output_type, Regex):
            raise TypeError(
                "Regex-based structured outputs are not supported by Ollama. "
                "Use an open source model in the meantime."
            )
        elif isinstance(output_type, CFG):
            raise TypeError(
                "CFG-based structured outputs are not supported by Ollama. "
                "Use an open source model in the meantime."
            )

        if output_type is None:
            return None
        elif isinstance(output_type, JsonSchema):
            return json.loads(output_type.schema)
        elif is_dataclass(output_type):
            schema = TypeAdapter(output_type).json_schema()
            return schema
        elif is_typed_dict(output_type):
            schema = TypeAdapter(output_type).json_schema()
            return schema
        elif is_pydantic_model(output_type):
            schema = output_type.model_json_schema()
            return schema
        elif is_genson_schema_builder(output_type):
            return output_type.to_json()
        else:
            type_name = getattr(output_type, "__name__", output_type)
            raise TypeError(
                f"The type `{type_name}` is not supported by Ollama. "
                "Consider using a local model instead."
            )


class Ollama(Model):
    """Thin wrapper around the `ollama.Client` client.

    This wrapper is used to convert the input and output types specified by the
    users at a higher level to arguments to the `ollama.Client` client.

    """

    def __init__(
        self,client: "OllamaClient", model_name: Optional[str] = None,
    ):
        """
        Parameters
        ----------
        client
            The `ollama.Client` client.
        model_name
            The name of the model to use.

        """
        self.client = client
        self.model_name = model_name
        self.type_adapter = OllamaTypeAdapter()

    def generate(self,
        model_input: str,
        output_type: Optional[Any] = None,
        **kwargs: Any,
    ) -> str:
        """Generate text using Ollama.

        Parameters
        ----------
        model_input
            The prompt based on which the model will generate a response.
        output_type
            The desired format of the response generated by the model. The
            output type must be of a type that can be converted to a JSON
            schema.
        **kwargs
            Additional keyword arguments to pass to the client.

        Returns
        -------
        str
            The text generated by the model.

        """
        if "model" not in kwargs and self.model_name is not None:
            kwargs["model"] = self.model_name

        response = self.client.generate(
            prompt=self.type_adapter.format_input(model_input),
            format=self.type_adapter.format_output_type(output_type),
            **kwargs,
        )
        return response.response

    def generate_stream(
        self,
        model_input: str,
        output_type: Optional[Any] = None,
        **kwargs: Any,
    ) -> Iterator[str]:
        """Stream text using Ollama.

        Parameters
        ----------
        model_input
            The prompt based on which the model will generate a response.
        output_type
            The desired format of the response generated by the model. The
            output type must be of a type that can be converted to a JSON
            schema.
        **kwargs
            Additional keyword arguments to pass to the client.

        Returns
        -------
        Iterator[str]
            An iterator that yields the text generated by the model.

        """
        if "model" not in kwargs and self.model_name is not None:
            kwargs["model"] = self.model_name

        response = self.client.generate(
            prompt=self.type_adapter.format_input(model_input),
            format=self.type_adapter.format_output_type(output_type),
            stream=True,
            **kwargs,
        )
        for chunk in response:
            yield chunk.response


def from_ollama(
    client: "OllamaClient", model_name: Optional[str] = None
) -> Ollama:
    """Create an Outlines `Ollama` model instance from an `ollama.Client`
    client.

    Parameters
    ----------
    client
        A `ollama.Client` client instance.
    model_name
        The name of the model to use.

    Returns
    -------
    Ollama
        An Outlines `Ollama` model instance.

    """
    return Ollama(client, model_name)
