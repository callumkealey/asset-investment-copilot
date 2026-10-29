from __future__ import annotations

import json
import os

from .tools import TOOLS, ToolRuntime, execute_tool

SYSTEM_INSTRUCTIONS = """
You are the decision-support copilot for a synthetic infrastructure capital-planning prototype.

Rules:
- Never invent project values, scores, budgets or data-quality findings.
- Use run_budget_scenario or compare_scenarios for numerical portfolio conclusions.
- Use get_project for project-specific facts.
- Use get_asset for current EAM asset condition, inspection metadata and asset-to-project reconciliation.
- Do not infer asset condition or inspection dates from project descriptions or general policy text.
- Do not describe asset data as fresh, stale or conflicting unless the available evidence supports that classification.
- Never modify asset records; asset lookups and recommendations are read-only.
- Use search_documents when the user asks for policy, regulatory or documentary evidence.
- Clearly distinguish structured portfolio evidence from retrieved documentary evidence.
- Treat recommendations as decision support, not autonomous approvals.
- Mention missing or incomplete data when it materially affects the answer.
- Keep answers concise and executive-friendly, but explain material trade-offs.
""".strip()


class CopilotAgent:
    def __init__(self, runtime: ToolRuntime, model: str | None = None):
        from openai import OpenAI

        if not os.getenv("OPENAI_API_KEY"):
            raise RuntimeError("OPENAI_API_KEY is not set")
        self.client = OpenAI()
        self.model = model or os.getenv("OPENAI_MODEL", "gpt-6-luna")
        self.runtime = runtime

    def ask(self, question: str, max_rounds: int = 6) -> dict:
        input_list = [{"role": "user", "content": question}]
        tool_trace: list[dict] = []

        for _ in range(max_rounds):
            response = self.client.responses.create(
                model=self.model,
                instructions=SYSTEM_INSTRUCTIONS,
                tools=TOOLS,
                input=input_list,
            )
            input_list += list(response.output)

            calls = [item for item in response.output if getattr(item, "type", None) == "function_call"]
            if not calls:
                return {"answer": response.output_text, "tool_trace": tool_trace}

            for call in calls:
                args = json.loads(call.arguments or "{}")
                result = execute_tool(self.runtime, call.name, args)
                tool_trace.append({"tool": call.name, "arguments": args, "result": result})
                input_list.append(
                    {
                        "type": "function_call_output",
                        "call_id": call.call_id,
                        "output": json.dumps(result, default=str),
                    }
                )

        return {
            "answer": "The agent reached its tool-call limit before producing a final answer.",
            "tool_trace": tool_trace,
        }
