package com.example;

import java.util.*;
import java.io.*;

public class UserService {
    private Map<String, User> userCache = new HashMap<>();

    // 违反命名规范：方法名应该小写开头
    public void GetUserById(String id) {
        if (id == null) {
            return;
        }
        User user = userCache.get(id);
        if (user == null) {
            // 空指针风险
            System.out.println(user.getName());
        }
    }

    // 违反并发规范：HashMap 不适合多线程环境
    public void addUser(String id, User user) {
        userCache.put(id, user);
    }

    // 违反异常规范：捕获通用异常
    public void processData() {
        try {
            FileInputStream fis = new FileInputStream("test.txt");
        } catch (Exception e) {
            // 不应该捕获通用 Exception
            e.printStackTrace();
        }
    }

    // 违反 SQL 规范：字符串拼接 SQL
    public List<User> findUsers(String name) {
        String sql = "SELECT * FROM users WHERE name = '" + name + "'";
        return new ArrayList<>();
    }
}

class User {
    private String name;
    private int age;

    public String getName() { return name; }
    public void setName(String name) { this.name = name; }
    public int getAge() { return age; }
    public void setAge(int age) { this.age = age; }
}
