"""Trusted projections of original state and confirmed original ledger observations.

No agent API exposes these snapshots. History means inspected results, not model
content lineage. The original callback is retained by every decorator.
"""
from contextvars import ContextVar
from contextlib import nullcontext
from copy import deepcopy
from functools import wraps
import json
import uuid

from policyweave.enforcement import caller_context
from policyweave.enforcement.telemetry import current_trace
from policy_port.binding import make_policy, CALLS

_AGENT = ContextVar('enrollment_agent', default=None)
_ORIGIN = ContextVar('enrollment_origin', default=None)


def state(world):
    if not hasattr(world, '_port_observations'):
        world._port_observations = {'id': uuid.uuid4().hex, 'receipts': {}, 'actions': {}, 'policies': {}, 'messages': {}}
    return world._port_observations


def scope_for(world, default):
    active = _AGENT.get()
    if active is not None and active['world'] is world:
        return active['role'], active['scope']
    return default, 'task' if default == 'advisor' else 'direct-registrar'


def symbol_list(value):
    if not isinstance(value, list) or any(type(v) is not str for v in value):
        raise ValueError('Original observed list must contain strings.')
    return value


def snapshot(app, role, scope, context, registry):
    """Complete request-version snapshot. Failed reads propagate, never empty sets."""
    request = context['request']
    q, action, args = request['id'], request['event'], request['parameters']
    fields = [('authenticated_actor', app.world.actor)]
    if action in {'enroll', 'reject', 'defer'}:
        fields.extend(('student_key', k) for k in list(app.world.students.keys()))
        fields.extend(('course_key', k) for k in list(app.world.catalog.keys()))
    if action == 'enroll':
        target, course = args.get('student_id'), args.get('course')
        # Scope selection protects private observations; authorization stays in rules.
        if target == app.world.actor and target in app.world.students and course in app.world.catalog:
            fields.extend(('completed_course', c) for c in symbol_list(app.world.students[target]['completed']))
            fields.extend(('required_prerequisite', c) for c in symbol_list(app.world.catalog[course]['requires']))
    if action in {'record_plan', 'ask_registrar'}:
        fields.extend(('requested_course', c) for c in symbol_list(app.spec['request']['courses']))
    fields.extend(state(app.world)['receipts'].get((role, scope), []))
    return [{'predicate': 'Field', 'args': [q, name, value]} for name, value in fields]


def refusal_for(app, role):
    def refusal(tool_name, feedback):
        codes = set(feedback['reasonCodes'])
        # Only these native errors are public for these exact actions. Combined
        # ownership/capability/inspection failures retain privacy masking.
        allowed = {'enroll': {'unknown_student', 'unknown_course', 'missing_prerequisites'},
                   'defer': {'unknown_student', 'unknown_course'}}.get(tool_name, set())
        public = sorted(codes) if codes and codes <= allowed else ['policy_refusal']
        result = {'status': 'error', 'reason': public[0],
                  'policy_feedback': {**feedback, 'reasonCodes': public}}
        if codes == {'authorization_error'}:
            result['reason'] = 'authorization_error'
            result['policy_feedback']['reasonCodes'] = ['authorization_error']
        if codes == {'unknown_tool'}:
            result['reason'] = 'unknown_tool'
            result['policy_feedback']['reasonCodes'] = ['unknown_tool']
        if tool_name == 'ask_registrar' and role == 'advisor' and codes == {'requested_course_required'}:
            result['reason'] = ('Use a requested catalog course ID, not a section ID. '
                                'Put the preferred section in context; the registrar chooses section_id separately.')
            result['requested_courses'] = deepcopy(app.spec['request']['courses'])
            result['policy_feedback']['reasonCodes'] = ['requested_course_required']
        return result
    return refusal


def dispatch(boundary):
    def decorate(body):
        @wraps(body)
        def checked(app, name, args):
            origin = _ORIGIN.get()
            role, scope = origin if origin is not None else scope_for(app.world, boundary)
            action = name
            if boundary == 'registrar' and name in {'read_catalog', 'read_enrollment_context', 'search_sections'}:
                action = 'registrar_' + name
            # Unknown tool handling belongs to the unchanged protocol validation
            # on the agent path. A direct unknown call cannot be evaluated under
            # the frozen call contract, so preserve its protocol error safely.
            if action not in CALLS:
                trace = current_trace()
                with trace.operation(role, name, args) if trace else nullcontext() as observation:
                    result = {'status': 'error', 'reason': 'unknown_tool'}
                    if observation is not None:
                        observation['value'] = result
                    return result
            key = (boundary, role, scope)
            policies = state(app.world)['policies']
            if key not in policies:
                policies[key] = make_policy(
                    facts=lambda c, r: snapshot(app, role, scope, c, r),
                    refusal=refusal_for(app, role),
                    completed=lambda result: not (isinstance(result, dict) and result.get('status') == 'error'))
            policy = policies[key]
            trace = current_trace()
            token = _ORIGIN.set((role, scope)) if boundary == 'advisor' and name != 'ask_registrar' else _ORIGIN.set(None)
            try:
                with trace.operation(role, name, args) if trace else nullcontext() as observation:
                    with caller_context(role):
                        # @policy retains the exact candidate original body for
                        # native boundary stack attribution, including blocks.
                        result = policy(name=action, arguments=args)(body)(app, name, args)
                    if observation is not None:
                        observation['value'] = result
                    if trace and name in {'enroll', 'reject', 'defer'}:
                        trace.event('state', 'environment', data={
                            'observation': 'post_dispatch_state', 'students': app.world.students,
                            'catalog': app.world.catalog, 'outcomes': app.outcomes})
                    return result
            finally:
                _ORIGIN.reset(token)
        return checked
    return decorate


def observe_world(body):
    @wraps(body)
    def wrapped(world, *args, **kwargs):
        result = body(world, *args, **kwargs)
        state(world)
        trace = current_trace()
        if trace:
            trace.participant('environment', kind='environment')
            trace.participant('runtime', kind='runtime')
            trace.participant('advisor', kind='agent')
            trace.participant('registrar', kind='agent')
            trace.participant(world.actor, kind='user')
            trace.event('state', 'environment', data={'observation': 'initial_state',
                        'actor': world.actor, 'now': world.now,
                        'students': world.students, 'catalog': world.catalog})
        return result
    return wrapped


def observe_log(body):
    @wraps(body)
    def wrapped(world, agent, kind, payload):
        result = body(world, agent, kind, payload)
        data = state(world)
        role, scope = scope_for(world, agent)
        key = (role, scope, payload.get('call_id'))
        if kind == 'action':
            data['actions'][key] = deepcopy(payload)
        if kind == 'observation' and key in data['actions']:
            action = data['actions'].pop(key)
            try:
                args = json.loads(action['arguments_json'])
            except (ValueError, TypeError):
                args = {}
            value = payload['result']
            name = action['tool']
            additions = []
            if isinstance(value, dict) and value.get('status') != 'error':
                target = args.get('student_id')
                if name == 'read_catalog' and 'courses' in value and 'external_note' in value:
                    additions.append(('catalog_receipt', f'{scope}:ledger-{world.events[-1]["step"]}:{payload["call_id"]}'))
                if target == world.actor:
                    if name == 'read_student' and 'completed' in value and 'enrolled' in value:
                        additions.append(('student_receipt', target))
                    if name == 'read_enrollment_context' and value.get('student_id') == target and 'active_appointment' in value:
                        additions.append(('context_receipt', target))
                    if name == 'search_sections' and value.get('course') == args.get('course') and value.get('availability_is_snapshot') is True:
                        additions.append(('section_receipt', args['course']))
                    if name == 'record_plan' and value.get('status') == 'planned' and value.get('student_id') == target:
                        additions.append(('plan_receipt', f'{scope}:ledger-{world.events[-1]["step"]}:{payload["call_id"]}'))
            data['receipts'].setdefault((role, scope), []).extend(additions)
        trace = current_trace()
        if trace:
            if kind == 'llm_response':
                trace.model_output(agent, payload['output'], stage='response')
            elif kind == 'final':
                trace.model_output(agent, payload, stage='final')
            trace.event('state', agent, data={'observation': 'original_ledger',
                        'step': world.events[-1]['step'], 'kind': kind, 'payload': payload})
        return result
    return wrapped


def observe_message(body):
    @wraps(body)
    def wrapped(world, sender, recipient, content):
        result = body(world, sender, recipient, content)
        mid = f'{state(world)["id"]}:ledger-{world.events[-1]["step"]}'
        state(world)['messages'][(sender, recipient)] = (mid, deepcopy(content))
        trace = current_trace()
        if trace:
            trace.message(sender, [recipient], content, phase='sent', message_id=mid)
        return result
    return wrapped


class ObservedClient:
    """Observes the original client callback; never changes model input or output."""
    def __init__(self, body, agent, scope):
        self.body, self.agent, self.scope = body, agent, uuid.uuid4().hex
        self.turn = 0
        self.received = set()

    def __getattr__(self, name):
        return getattr(self.body, name)

    def create(self, instructions, history, tools):
        trace = current_trace()
        self.turn += 1
        if trace:
            # This is the real consumption boundary for returning tool results.
            for item in history:
                if item.get('type') == 'function_call_output' and item['call_id'] not in self.received:
                    self.received.add(item['call_id'])
                    msg = state(self.agent.world)['messages'].get(('registrar', 'advisor'))
                    if self.agent.name == 'advisor' and msg:
                        try:
                            matches = json.loads(item['output']) == msg[1]
                        except (ValueError, TypeError):
                            matches = False
                        if matches:
                            trace.message('registrar', ['advisor'], msg[1], phase='received', message_id=msg[0])
        result = self.body.create(instructions, history, tools)
        if trace:
            # Versioned opaque handles for actual direct snapshots. No private
            # history bytes are exported and no unrelated task history is added.
            cid = f'{self.scope}:turn-{self.turn}'
            inputs = [cid + ':instructions', cid + ':tools'] + [cid + f':history-{i}' for i in range(len(history))]
            trace.source('runtime', inputs[0])
            trace.source('runtime', inputs[1])
            trace.context(self.agent.name, cid, inputs=[cid], outputs=[cid + ':output'], complete=False)
            trace.context(self.agent.name, cid + ':assembly', inputs=inputs, outputs=[cid], complete=False)
        return result


def observe_agent(body):
    @wraps(body)
    def wrapped(agent, context):
        scope = 'task' if agent.name == 'advisor' else uuid.uuid4().hex
        token = _AGENT.set({'world': agent.world, 'role': agent.name, 'scope': scope})
        origin = _ORIGIN.set(None)
        client = agent.client
        agent.client = ObservedClient(client, agent, scope)
        trace = current_trace()
        if trace:
            trace.participant(agent.name, kind='agent')
            msg = state(agent.world)['messages'].get(('advisor', 'registrar'))
            if agent.name == 'registrar' and msg and context.get('proposal') == msg[1]:
                trace.message('advisor', ['registrar'], msg[1], phase='received', message_id=msg[0])
        try:
            return body(agent, context)
        finally:
            agent.client = client
            _ORIGIN.reset(origin)
            _AGENT.reset(token)
    return wrapped


def observe_completion(body):
    @wraps(body)
    def wrapped(app, *args, **kwargs):
        try:
            value = body(app, *args, **kwargs)
            trace = current_trace()
            if trace:
                trace.model_output('advisor', value, stage='application_reply')
            return value
        finally:
            trace = current_trace()
            if trace:
                trace.event('state', 'environment', data={'observation': 'final_state',
                            'students': app.world.students, 'catalog': app.world.catalog,
                            'outcomes': app.outcomes})
    return wrapped
