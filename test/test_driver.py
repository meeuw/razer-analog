"""
Driver tests
"""
from unittest import IsolatedAsyncioTestCase
import asyncio
import razer_analog.driver
import evdev

RAZER_KEY_Q = 17
RAZER_KEY_H = 36
RAZER_KEY_FN = 59
RAZER_KEY_ESC = 110
RAZER_KEY_LEFTMETA = 127
RAZER_KEY_A = 31
EVDEV_KEY_Q = evdev.ecodes.ecodes["KEY_Q"]
EVDEV_KEY_H = evdev.ecodes.ecodes["KEY_H"]
EVDEV_KEY_FN = evdev.ecodes.ecodes["KEY_FN"]
EVDEV_KEY_ESC = evdev.ecodes.ecodes["KEY_ESC"]
EVDEV_KEY_LEFTMETA = evdev.ecodes.ecodes["KEY_LEFTMETA"]
EVDEV_KEY_GRAVE = evdev.ecodes.ecodes["KEY_GRAVE"]
EVDEV_KEY_A = evdev.ecodes.ecodes["KEY_A"]
EVDEV_ABS_HAT0X = evdev.ecodes.ecodes["ABS_HAT0X"]


class Test(IsolatedAsyncioTestCase):
    """
    Test Case
    """

    def setUp(self):
        self.pressed_queue = asyncio.Queue()
        self.user_input_queue = asyncio.Queue()
        self.virtual_keyboard = razer_analog.driver.virtual_keyboard(
            self.pressed_queue, self.user_input_queue
        )

    async def get_all(self):
        """
        Read until both queues are empty
        """
        result = []
        while not self.pressed_queue.empty() or not self.user_input_queue.empty():
            result.append(await self.user_input_queue.get())
        return result

    async def test_simple_keypressed(self):
        """
        Test simple keypressed
        """

        async def _tests():
            await self.pressed_queue.put({RAZER_KEY_Q: 129})
            await self.pressed_queue.put({RAZER_KEY_Q: 0})
            assert await self.get_all() == [(1, EVDEV_KEY_Q, 1), (1, EVDEV_KEY_Q, 0)]

            tasks.cancel()

        tasks = asyncio.gather(self.virtual_keyboard, _tests())
        try:
            await tasks
        except asyncio.exceptions.CancelledError:
            pass

    async def test_analog_keypressed(self):
        """
        Test analog keypressed
        """

        async def _tests():
            await self.pressed_queue.put({RAZER_KEY_H: 10})
            await self.pressed_queue.put({RAZER_KEY_H: 50})
            await self.pressed_queue.put({RAZER_KEY_H: 129})
            await self.pressed_queue.put({RAZER_KEY_H: 0})
            assert await self.get_all() == [
                (3, EVDEV_ABS_HAT0X, 10),
                (3, EVDEV_ABS_HAT0X, 50),
                (3, EVDEV_ABS_HAT0X, 129),
                (1, EVDEV_KEY_H, 1),
                (3, EVDEV_ABS_HAT0X, 0),
                (1, EVDEV_KEY_H, 0),
            ]

            tasks.cancel()

        tasks = asyncio.gather(self.virtual_keyboard, _tests())
        try:
            await tasks
        except asyncio.exceptions.CancelledError:
            pass

    async def test_hold_keypressed(self):
        """
        Test hold keypressed
        """

        async def _tests():
            await self.pressed_queue.put({RAZER_KEY_Q: 129})
            await asyncio.sleep(0.3)
            await self.pressed_queue.put({RAZER_KEY_Q: 0})
            assert await self.get_all() == [
                (1, EVDEV_KEY_Q, 1),
                (1, EVDEV_KEY_Q, 2),
                (1, EVDEV_KEY_Q, 2),
                (1, EVDEV_KEY_Q, 2),
                (1, EVDEV_KEY_Q, 0),
            ]

            tasks.cancel()

        tasks = asyncio.gather(self.virtual_keyboard, _tests())
        try:
            await tasks
        except asyncio.exceptions.CancelledError:
            pass

    async def test_fn_keypressed(self):
        """
        Test fn keypressed
        """

        async def _tests():
            # Release ESC first
            await self.pressed_queue.put(
                {
                    RAZER_KEY_FN: 129,
                    RAZER_KEY_ESC: 129,
                }
            )

            await self.pressed_queue.put(
                {
                    RAZER_KEY_FN: 129,
                    RAZER_KEY_ESC: 0,
                }
            )
            await self.pressed_queue.put(
                {
                    RAZER_KEY_FN: 0,
                    RAZER_KEY_ESC: 0,
                }
            )
            assert await self.get_all() == [
                (1, EVDEV_KEY_FN, 1),
                (1, EVDEV_KEY_GRAVE, 1),
                (1, EVDEV_KEY_GRAVE, 0),
                (1, EVDEV_KEY_FN, 0),
            ]

            # Release Fn first
            await self.pressed_queue.put(
                {
                    RAZER_KEY_FN: 129,
                    RAZER_KEY_ESC: 129,
                }
            )

            await self.pressed_queue.put(
                {
                    RAZER_KEY_FN: 0,
                    RAZER_KEY_ESC: 129,
                }
            )
            await self.pressed_queue.put(
                {
                    RAZER_KEY_FN: 0,
                    RAZER_KEY_ESC: 0,
                }
            )
            assert await self.get_all() == [
                (1, EVDEV_KEY_FN, 1),
                (1, EVDEV_KEY_GRAVE, 1),
                (1, EVDEV_KEY_FN, 0),
                (1, EVDEV_KEY_GRAVE, 0),
                (1, 1, 1),
                (1, 1, 0),
            ]

            # Release Fn at the same time
            await self.pressed_queue.put(
                {
                    RAZER_KEY_FN: 129,
                    RAZER_KEY_ESC: 129,
                }
            )

            await self.pressed_queue.put(
                {
                    RAZER_KEY_FN: 0,
                    RAZER_KEY_ESC: 0,
                }
            )
            assert await self.get_all() == [
                (1, EVDEV_KEY_FN, 1),
                (1, EVDEV_KEY_GRAVE, 1),
                (1, EVDEV_KEY_FN, 0),
                (1, EVDEV_KEY_GRAVE, 0),
            ]

            # Fn on non existing key
            await self.pressed_queue.put(
                {
                    RAZER_KEY_FN: 129,
                    RAZER_KEY_A: 129,
                }
            )

            await self.pressed_queue.put(
                {
                    RAZER_KEY_FN: 129,
                    RAZER_KEY_A: 0,
                }
            )
            await self.pressed_queue.put(
                {
                    RAZER_KEY_FN: 0,
                    RAZER_KEY_A: 0,
                }
            )
            assert await self.get_all() == [
                (1, EVDEV_KEY_FN, 1),
                (1, EVDEV_KEY_FN, 0),
            ]
            tasks.cancel()

        tasks = asyncio.gather(self.virtual_keyboard, _tests())
        try:
            await tasks
        except asyncio.exceptions.CancelledError:
            pass

    async def test_meta_keypressed(self):
        """
        Test fn keypressed (by meta)
        """

        async def _tests():
            # Hold left meta with FN unpressed
            await self.pressed_queue.put(
                {
                    RAZER_KEY_FN: 129,
                    RAZER_KEY_LEFTMETA: 0,
                }
            )
            await self.pressed_queue.put(
                {
                    RAZER_KEY_FN: 129,
                    RAZER_KEY_LEFTMETA: 0,
                }
            )
            assert await self.get_all() == [(1, EVDEV_KEY_FN, 1)]

            # Release left meta first
            await self.pressed_queue.put(
                {
                    RAZER_KEY_FN: 129,
                    RAZER_KEY_LEFTMETA: 129,
                }
            )

            await self.pressed_queue.put(
                {
                    RAZER_KEY_FN: 129,
                    RAZER_KEY_LEFTMETA: 0,
                }
            )
            await self.pressed_queue.put(
                {
                    RAZER_KEY_FN: 0,
                    RAZER_KEY_LEFTMETA: 0,
                }
            )
            assert await self.get_all() == [
                (1, EVDEV_KEY_LEFTMETA, 1),
                (1, EVDEV_KEY_FN, 0),
                (1, EVDEV_KEY_LEFTMETA, 0),
                (1, EVDEV_KEY_FN, 1),
                (1, EVDEV_KEY_FN, 0),
            ]

            # Release Fn first
            await self.pressed_queue.put(
                {
                    RAZER_KEY_FN: 129,
                    RAZER_KEY_LEFTMETA: 129,
                }
            )

            await self.pressed_queue.put(
                {
                    RAZER_KEY_FN: 0,
                    RAZER_KEY_LEFTMETA: 129,
                }
            )
            await self.pressed_queue.put(
                {
                    RAZER_KEY_FN: 0,
                    RAZER_KEY_LEFTMETA: 0,
                }
            )
            assert await self.get_all() == [
                (1, EVDEV_KEY_FN, 1),
                (1, EVDEV_KEY_LEFTMETA, 1),
                (1, EVDEV_KEY_FN, 0),
                (1, EVDEV_KEY_LEFTMETA, 0),
                (1, EVDEV_KEY_FN, 1),
                (1, EVDEV_KEY_FN, 0),
            ]

            # Release Fn at the same time
            await self.pressed_queue.put(
                {
                    RAZER_KEY_FN: 129,
                    RAZER_KEY_LEFTMETA: 129,
                }
            )

            await self.pressed_queue.put(
                {
                    RAZER_KEY_FN: 0,
                    RAZER_KEY_LEFTMETA: 0,
                }
            )
            result = await self.get_all()
            assert result == [
                (1, EVDEV_KEY_FN, 1),
                (1, EVDEV_KEY_LEFTMETA, 1),
                (1, EVDEV_KEY_FN, 0),
                (1, EVDEV_KEY_LEFTMETA, 0),
            ]
            tasks.cancel()

        tasks = asyncio.gather(self.virtual_keyboard, _tests())
        try:
            await tasks
        except asyncio.exceptions.CancelledError:
            pass
