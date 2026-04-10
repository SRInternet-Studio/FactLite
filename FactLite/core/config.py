from .actions import ReturnBest, FallbackAction
from .rules import BaseRule

class Config:
    def __init__(self, rule: BaseRule = None, 
                 max_retries: int = 2, 
                 on_fail: FallbackAction = ReturnBest()):
        """Initialize the configuration for the FactLite framework"""
        
        self.rule = rule
        self.max_retries = max_retries
        self.on_fail = on_fail