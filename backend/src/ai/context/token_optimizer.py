import tiktoken
from typing import Dict, List, Any, Optional

class TokenOptimizer:
    def __init__(self):
        self.encoder = tiktoken.encoding_for_model("gpt-3.5-turbo")
        
    def count_tokens(self, text: str) -> int:
        return len(self.encoder.encode(text))
        
    def truncate_to_token_limit(self, text: str, limit: int) -> str:
        tokens = self.encoder.encode(text)
        if len(tokens) <= limit:
            return text
        return self.encoder.decode(tokens[:limit])
        
    def optimize_messages(self, messages: List[Dict[str, Any]], budget: int) -> List[Dict[str, Any]]:
        total_tokens = sum(self.count_tokens(msg['content']) for msg in messages)
        if total_tokens <= budget:
            return messages
            
        # Keep most recent messages within budget
        optimized_messages = []
        current_tokens = 0
        
        for msg in reversed(messages):
            msg_tokens = self.count_tokens(msg['content'])
            if current_tokens + msg_tokens <= budget:
                optimized_messages.insert(0, msg)
                current_tokens += msg_tokens
            else:
                # Try to fit a truncated version of the message
                remaining_tokens = budget - current_tokens
                if remaining_tokens > 100:  # Only if we can keep a meaningful portion
                    truncated_content = self.truncate_to_token_limit(msg['content'], remaining_tokens)
                    msg['content'] = truncated_content
                    optimized_messages.insert(0, msg)
                break
                
        return optimized_messages
        
    def optimize_context(self, context: Dict[str, Any], budget: int) -> Dict[str, Any]:
        total_tokens = sum(
            self.count_tokens(str(value))
            for value in context.values()
            if isinstance(value, (str, int, float))
        )
        
        if total_tokens <= budget:
            return context
            
        # Prioritize optimization based on content type
        priorities = ['system', 'user', 'assistant', 'tool']
        optimized = {}
        current_tokens = 0
        
        for priority in priorities:
            if priority in context:
                content = context[priority]
                tokens = self.count_tokens(str(content))
                if current_tokens + tokens <= budget:
                    optimized[priority] = content
                    current_tokens += tokens
                else:
                    remaining_tokens = budget - current_tokens
                    if remaining_tokens > 100:
                        truncated = self.truncate_to_token_limit(str(content), remaining_tokens)
                        optimized[priority] = truncated
                        current_tokens += remaining_tokens
                    break
                    
        return optimized