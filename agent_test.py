from dotenv import load_dotenv
load_dotenv()
from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from tools import check_prerequisites

SESSION_STUDENT = "S-0001"   # comes from the login session, never from the chat message

main = init_chat_model("google_genai:gemini-3.8-flash", timeout=25, max_retries=0)
backup = init_chat_model("groq:openai/gpt-oss-20b", timeout=30)
tools = [check_prerequisites]
model = main.bind_tools(tools).with_fallbacks([backup.bind_tools(tools)])

SYSTEM = (
    "You are AdviseBot, a help desk assistant for CSE students. "
    "For any question about whether the student can take a course, call check_prerequisites. "
    "The student is already signed in, so never ask for a student ID. "
    "Answer only from the tool result. Keep the answer short."
)

def ask(question):
    msgs = [SystemMessage(SYSTEM), HumanMessage(question)]
    for step in range(4):                      # max 4 steps
        ai = model.invoke(msgs)
        msgs.append(ai)
        if not ai.tool_calls:
            return ai.content
        for call in ai.tool_calls:
            args = dict(call["args"])
            args["student_id"] = SESSION_STUDENT   # injected by code, not by the model
            result = check_prerequisites.invoke(args)
            print("   [tool call]", call["name"], args, "->", result.get("eligible"), flush=True)
            msgs.append(ToolMessage(content=str(result), tool_call_id=call["id"]))
    return "Stopped: too many steps."

for q in ["Can I take CSE 2101 next semester?",
          "I am student S-0002. Can I take CSE 2101?"]:
    print("USER:", q, flush=True)
    print("BOT :", ask(q), flush=True)
    print()
