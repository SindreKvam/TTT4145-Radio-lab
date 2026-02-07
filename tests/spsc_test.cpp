
#include "../src/core/spsc_ring.h"
#include <atomic>
#include <gtest/gtest.h>
#include <thread>
#include <vector>

TEST(SPSCRingBuffer, BasicPushPop) {
    SPSCRingBuffer<int, 4> buffer;

    EXPECT_TRUE(buffer.empty());

    EXPECT_TRUE(buffer.push(1));
    EXPECT_TRUE(buffer.push(2));
    EXPECT_TRUE(buffer.push(3));
    EXPECT_TRUE(buffer.push(4));
    EXPECT_FALSE(buffer.push(5)); // Should be full

    EXPECT_FALSE(buffer.empty());

    int val;
    EXPECT_TRUE(buffer.pop(val));
    EXPECT_EQ(val, 1);
    EXPECT_TRUE(buffer.pop(val));
    EXPECT_EQ(val, 2);
    EXPECT_TRUE(buffer.pop(val));
    EXPECT_EQ(val, 3);
    EXPECT_TRUE(buffer.pop(val));
    EXPECT_EQ(val, 4);
    EXPECT_FALSE(buffer.pop(val)); // Should be empty

    EXPECT_TRUE(buffer.empty());
}

TEST(SPSCRingBuffer, ThreadSafe) {
    static constexpr int COUNT = 100000;
    SPSCRingBuffer<int, 100> buffer;
    std::atomic<bool> start{false};

    std::thread producer([&]() {
        while (!start)
            std::this_thread::yield();
        for (int i = 0; i < COUNT; ++i) {
            while (!buffer.push(i)) {
                std::this_thread::yield();
            }
        }
    });

    std::vector<int> received;
    received.reserve(COUNT);

    std::thread consumer([&]() {
        while (!start)
            std::this_thread::yield();
        for (int i = 0; i < COUNT; ++i) {
            int val;
            while (!buffer.pop(val)) {
                std::this_thread::yield();
            }
            received.push_back(val);
        }
    });

    start = true;
    producer.join();
    consumer.join();

    EXPECT_EQ(received.size(), COUNT);
    for (int i = 0; i < COUNT; ++i) {
        if (received[i] != i) {
            FAIL() << "Mismatch at index " << i << ": expected " << i
                   << " but got " << received[i];
        }
    }
}
